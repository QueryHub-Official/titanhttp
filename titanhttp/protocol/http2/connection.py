import socket
import struct
from typing import Dict, Optional, Tuple
from ...core.framing import HTTP2Frame
from .frames import FrameTypes, FrameFlags
from .hpack import HPACKDecoder, HPACEncoder
from .stream import HTTP2Stream


class HTTP2Connection:
    """HTTP/2 connection manager."""

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.encoder = HPACEncoder()
        self.decoder = HPACKDecoder()
        self.streams: Dict[int, HTTP2Stream] = {}
        self.next_stream_id = 1
        self._buffer = bytearray()
        self._window = 65535

    def send_preface(self):
        self.sock.sendall(b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n")
        self._send_frame(FrameTypes.SETTINGS, 0, 0, b"")

    def start_stream(self) -> int:
        sid = self.next_stream_id
        self.next_stream_id += 2
        self.streams[sid] = HTTP2Stream(sid)
        return sid

    def send_headers(self, stream_id: int, headers: Dict[str, str], end_stream: bool = False):
        payload = self.encoder.encode(headers)
        flags = FrameFlags.END_HEADERS
        if end_stream:
            flags |= FrameFlags.END_STREAM
        self._send_frame(FrameTypes.HEADERS, flags, stream_id, payload)

    def send_data(self, stream_id: int, data: bytes, end_stream: bool = False):
        flags = FrameFlags.END_STREAM if end_stream else 0
        self._send_frame(FrameTypes.DATA, flags, stream_id, data)

    def read_frame(self) -> HTTP2Frame:
        while len(self._buffer) < 9:
            self._buffer.extend(self.sock.recv(4096))
        length = struct.unpack(">I", b"\x00" + self._buffer[:3])[0]
        while len(self._buffer) < 9 + length:
            self._buffer.extend(self.sock.recv(4096))
        frame = HTTP2Frame.from_bytes(bytes(self._buffer[:9]), bytes(self._buffer[9 : 9 + length]))
        self._buffer = self._buffer[9 + length :]
        return frame

    def _send_frame(self, ftype: int, flags: int, stream_id: int, payload: bytes):
        frame = HTTP2Frame(len(payload), ftype, flags, stream_id, payload)
        self.sock.sendall(frame.to_bytes())

    def read_stream_response(self, stream_id: int) -> Tuple[int, Dict[str, str], bytes]:
        headers = {}
        body = bytearray()
        while True:
            frame = self.read_frame()
            if frame.stream_id != stream_id:
                continue
            if frame.type == FrameTypes.HEADERS:
                h = self.decoder.decode(frame.payload)
                headers.update(h)
                if frame.flags & FrameFlags.END_HEADERS:
                    pass
                if frame.flags & FrameFlags.END_STREAM:
                    break
            elif frame.type == FrameTypes.DATA:
                body.extend(frame.payload)
                if frame.flags & FrameFlags.END_STREAM:
                    break
            elif frame.type == FrameTypes.RST_STREAM:
                raise ProtocolError(f"Stream {stream_id} reset")
        status = int(headers.get(":status", 200))
        del headers[":status"]
        return status, headers, bytes(body)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
