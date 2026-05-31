import socket
from typing import Optional


class SocketBuffer:
    """Efficient socket read buffer with line parsing."""

    def __init__(self, sock: socket.socket, chunk_size: int = 8192):
        self.sock = sock
        self.chunk_size = chunk_size
        self._buffer = bytearray()

    def read(self, n: int) -> bytes:
        """Read exactly n bytes."""
        while len(self._buffer) < n:
            chunk = self.sock.recv(min(self.chunk_size, n - len(self._buffer)))
            if not chunk:
                raise ConnectionError("Connection closed while reading")
            self._buffer.extend(chunk)
        data = bytes(self._buffer[:n])
        self._buffer = self._buffer[n:]
        return data

    def readline(self, max_length: int = 65536) -> bytes:
        """Read until LF."""
        while True:
            idx = self._buffer.find(b"\n")
            if idx != -1:
                line = bytes(self._buffer[: idx + 1])
                self._buffer = self._buffer[idx + 1 :]
                return line
            chunk = self.sock.recv(self.chunk_size)
            if not chunk:
                line = bytes(self._buffer)
                self._buffer = bytearray()
                return line
            self._buffer.extend(chunk)
            if len(self._buffer) > max_length:
                raise ConnectionError("Header line too long")

    def unread(self, data: bytes):
        """Push data back to buffer."""
        self._buffer = bytearray(data) + self._buffer

    def has_data(self) -> bool:
        return len(self._buffer) > 0

    def clear(self):
        self._buffer = bytearray()
