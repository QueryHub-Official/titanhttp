import socket
from typing import Dict, Optional, Tuple
from ...core.buffer import SocketBuffer
from ...core.parser import HTTPParser
from .body_reader import BodyReader


class HTTP1Connection:
    """HTTP/1.1 connection handler."""

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buf = SocketBuffer(sock)
        self.closed = False

    def send_request(
        self, method: str, path: str, headers: Dict[str, str], body: Optional[bytes] = None
    ):
        lines = [f"{method} {path} HTTP/1.1"]
        for k, v in headers.items():
            lines.append(f"{k}: {v}")
        if body and "Content-Length" not in headers:
            lines.append(f"Content-Length: {len(body)}")
        request = ("\r\n".join(lines) + "\r\n\r\n").encode()
        if body:
            request += body
        self.sock.sendall(request)

    def read_response(self) -> Tuple[int, Dict[str, str], bytes]:
        version, status, reason = HTTPParser.parse_status_line(self.buf)
        headers = HTTPParser.parse_headers(self.buf)
        body = BodyReader.read(self.buf, headers)
        # Detect connection close
        conn = headers.get("Connection", "").lower()
        if conn == "close" or status < 200:
            self.closed = True
        return status, headers, body

    def close(self):
        self.closed = True
        try:
            self.sock.close()
        except Exception:
            pass
