import socket
from typing import Optional
from ..protocol.socks import SOCKSProxy
from ..utils.url import URL


class ProxyTunnel:
    @staticmethod
    def connect_http_connect(proxy_url: str, target_host: str, target_port: int, timeout: float = 30) -> socket.socket:
        p = URL(proxy_url)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((p.host, p.port))
        req = f"CONNECT {target_host}:{target_port} HTTP/1.1\r\nHost: {target_host}:{target_port}\r\n\r\n"
        sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += sock.recv(1024)
        if b"200" not in resp.split(b"\r\n")[0]:
            raise ConnectionError("Proxy CONNECT failed")
        return sock

    @staticmethod
    def connect_socks(proxy_url: str, target_host: str, target_port: int) -> socket.socket:
        p = URL(proxy_url)
        if p.scheme in ("socks4", "socks4a"):
            return SOCKSProxy.connect_via_socks4(p.host, p.port, target_host, target_port)
        elif p.scheme == "socks5":
            return SOCKSProxy.connect_via_socks5(p.host, p.port, target_host, target_port, p.username, p.password)
        raise ValueError(f"Unsupported proxy scheme: {p.scheme}")
