import socket
import time
import json
from typing import Dict, Any, Optional, Tuple, Union
from urllib.parse import urlparse

from ..types import HTTPMethod, URLComponents
from ..exceptions import RetryExhausted, CircuitBreakerOpen
from ..protocol.http1 import HTTP1Connection
from ..protocol.http2 import HTTP2Connection
from ..protocol.websocket import WebSocketClient
from ..transport.socket_factory import SocketFactory
from ..transport.tls import TLSContext
from ..transport.dns import DNSCache
from ..transport.pool import ConnectionPool, PooledConnection
from ..transport.proxy_tunnel import ProxyTunnel
from ..utils.url import URL
from ..utils.headers import HeaderMap
from ..utils.body import BodyBuilder
from ..utils.compress import decompress
from ..utils.graphql import GraphQLHelper

from .request import Request
from .response import Response
from .session import SessionState
from .retry import RetryConfig, RetryController
from .dedupe import DedupeManager
from .cache.manager import CacheManager
from .cookie.jar import CookieJar
from .auth.basic import BasicAuth
from .auth.aws import AWSAuth
from .proxy_rotator import ProxyRotator
from .ratelimit import TokenBucketRateLimiter, RateLimit
from .adaptive import AdaptiveTimeout
from .stream import StreamDownloader


class TitanClient:
    def __init__(
        self,
        http2: bool = True,
        verify: bool = True,
        ca_bundle: Optional[str] = None,
        cert_pin: Optional[str] = None,
        timeout: float = 30.0,
        max_redirects: int = 10,
        proxy: Optional[str] = None,
        proxy_rotator: Optional[ProxyRotator] = None,
        retry: Optional[RetryConfig] = None,
        cache: Optional[CacheManager] = None,
        cookie_jar: Optional[CookieJar] = None,
        dedupe: bool = True,
        adaptive_timeout: bool = True,
        max_connections: int = 10,
        rate_limit: Optional[RateLimit] = None,
    ):
        self.http2 = http2
        self.tls = TLSContext(verify, ca_bundle, cert_pin)
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.proxy = proxy
        self.proxy_rotator = proxy_rotator
        self.retry = retry or RetryConfig()
        self.cache = cache
        self.session = SessionState(cookie_jar or CookieJar(), cache)
        self.dedupe = DedupeManager() if dedupe else None
        self.adaptive = AdaptiveTimeout() if adaptive_timeout else None
        self.pool = ConnectionPool(max_connections)
        self.dns = DNSCache()
        self.rate_limiter = TokenBucketRateLimiter(rate_limit) if rate_limit else None
        self.retry_ctrl = RetryController(self.retry)
        self.stream_downloader = StreamDownloader(self)

    def get(self, url: str, **kwargs) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        return self.request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs) -> Response:
        return self.request("PATCH", url, **kwargs)

    def head(self, url: str, **kwargs) -> Response:
        return self.request("HEAD", url, **kwargs)

    def options(self, url: str, **kwargs) -> Response:
        return self.request("OPTIONS", url, **kwargs)

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict, str, bytes]] = None,
        json: Optional[Any] = None,
        files: Optional[Dict] = None,
        auth: Optional[Tuple[str, str]] = None,
        allow_redirects: bool = True,
        stream: bool = False,
        timeout: Optional[float] = None,
    ) -> Response:
        req = Request(
            method=HTTPMethod(method.upper()),
            url=URL(url).components,
            headers=HeaderMap(headers or {}),
            body=data,
            json=json,
            files=files,
            auth=auth,
            timeout=timeout or self.timeout,
            allow_redirects=allow_redirects,
            stream=stream,
        )
        req.prepare_body()

        # Dedupe
        if self.dedupe and req.is_idempotent:
            dup = self.dedupe.check(req.method.value, req.url.origin + req.url.request_uri, req.body)
            if dup:
                return dup

        # Retry wrapper
        def _do():
            return self._send(req, 0)

        try:
            resp = self.retry_ctrl.execute(req.url.host, _do)
        except (RetryExhausted, CircuitBreakerOpen):
            raise

        # Dedupe store
        if self.dedupe and req.is_idempotent:
            self.dedupe.store(req.method.value, req.url.origin + req.url.request_uri, req.body, resp)

        return resp

    def _send(self, req: Request, redirect_count: int) -> Response:
        parsed = req.url

        # Proxy selection
        proxy_url = None
        if self.proxy_rotator:
            proxy_url = self.proxy_rotator.get_proxy()
        elif self.proxy:
            proxy_url = self.proxy

        # DNS
        addr = self.dns.resolve(parsed.host, parsed.port)

        # Rate limit
        if self.rate_limiter:
            self.rate_limiter.acquire(parsed.host)

        # Get or create connection
        conn = self.pool.get(parsed.scheme, parsed.host, parsed.port)
        if conn is None:
            raw_sock = SocketFactory.create_tcp_socket(addr[0])
            if proxy_url:
                p = URL(proxy_url)
                if p.scheme in ("http", "https"):
                    raw_sock = ProxyTunnel.connect_http_connect(proxy_url, parsed.host, parsed.port)
                else:
                    raw_sock = ProxyTunnel.connect_socks(proxy_url, parsed.host, parsed.port)
            else:
                SocketFactory.connect(raw_sock, addr[4], self._timeout_for(parsed.host))

            # TLS
            if parsed.scheme == "https":
                raw_sock, protocol = self.tls.wrap(raw_sock, parsed.host)
            else:
                protocol = "http/1.1"

            conn = PooledConnection(raw_sock, protocol)

        # Send via protocol
        sock = conn.sock
        path = parsed.request_uri
        start = time.time()

        if conn.meta.protocol == "h2" and self.http2:
            h2 = HTTP2Connection(sock)
            h2.send_preface()
            sid = h2.start_stream()
            h2_headers = {
                ":method": req.method.value,
                ":path": path,
                ":scheme": parsed.scheme,
                ":authority": parsed.netloc,
                **dict(req.headers),
            }
            h2.send_headers(sid, h2_headers, end_stream=(req.body is None))
            if req.body:
                h2.send_data(sid, req.body, end_stream=True)
            status, resp_headers, resp_body = h2.read_stream_response(sid)
        else:
            h1 = HTTP1Connection(sock)
            h1.send_request(req.method.value, path, dict(req.headers), req.body)
            status, resp_headers, resp_body = h1.read_response()

        elapsed = time.time() - start

        # Adaptive record
        if self.adaptive:
            self.adaptive.record(parsed.host, elapsed)

        # Decompress
        enc = resp_headers.get("Content-Encoding", "")
        if enc and not req.stream:
            resp_body = decompress(resp_body, enc)

        resp = Response(
            status=status,
            headers=HeaderMap(resp_headers),
            content=resp_body,
            url=parsed.origin + path,
            elapsed=elapsed,
        )

        # Pool return
        if resp_headers.get("Connection", "").lower() != "close":
            self.pool.put(parsed.scheme, parsed.host, parsed.port, conn)
        else:
            conn.sock.close()

        # Redirect
        if req.allow_redirects and resp.is_redirect and redirect_count < self.max_redirects:
            loc = resp.headers.get("Location")
            if loc:
                new_url = loc if loc.startswith("http") else parsed.origin + loc
                if resp.status == 303 and req.method != HTTPMethod.GET:
                    req.method = HTTPMethod.GET
                    req.body = None
                    req.headers.pop("Content-Length", None)
                    req.headers.pop("Content-Type", None)
                req.url = URL(new_url).components
                return self._send(req, redirect_count + 1)

        # Cache
        if self.cache and req.method == HTTPMethod.GET:
            self.cache.store(
                req.method.value,
                req.url.origin + req.url.request_uri,
                dict(req.headers),
                {"status": resp.status, "headers": dict(resp.headers), "content": resp.content.decode("utf-8", errors="replace"), "url": resp.url, "elapsed": resp.elapsed},
                dict(resp.headers),
            )

        # Cookies
        for sc in resp.headers.getall("Set-Cookie"):
            self.session.cookie_jar.set_cookie(parsed.host, sc)

        return resp

    def _timeout_for(self, host: str) -> float:
        if self.adaptive:
            return self.adaptive.timeout_for(host, self.timeout)
        return self.timeout

    def websocket(self, url: str) -> WebSocketClient:
        parsed = URL(url).components
        addr = self.dns.resolve(parsed.host, parsed.port)
        raw_sock = SocketFactory.create_tcp_socket(addr[0])
        SocketFactory.connect(raw_sock, addr[4], self.timeout)
        if parsed.scheme == "wss":
            raw_sock, _ = self.tls.wrap(raw_sock, parsed.host)
        ws = WebSocketClient(raw_sock, url)
        ws.handshake(parsed.host, parsed.path or "/")
        return ws

    def graphql(self, endpoint: str) -> GraphQLHelper:
        return GraphQLHelper(self, endpoint)

    def download(self, url: str, path: str, **kwargs) -> str:
        return self.stream_downloader.download(url, path, **kwargs)

    def close(self):
        self.pool.close_all()
