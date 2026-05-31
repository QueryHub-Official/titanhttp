import socket
import threading
import time
from typing import Callable, Dict, List, Optional
from .handshake import WSHandshake
from .frame import WSFrame, OpCode


class WebSocketClient:
    def __init__(self, sock: socket.socket, url: str):
        self.sock = sock
        self.url = url
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._fragments: bytearray = bytearray()
        self._frag_type: Optional[int] = None
        self._send_lock = threading.Lock()

    def handshake(self, host: str, path: str):
        key = WSHandshake.generate_key()
        req = WSHandshake.build_request(host, path, key).encode()
        self.sock.sendall(req)
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self.sock.recv(1024)
        if not WSHandshake.validate_response(resp, key):
            raise ConnectionError("WebSocket handshake failed")

    def on(self, event: str, handler: Callable):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def send(self, data: str or bytes or dict, opcode: Optional[int] = None):
        if isinstance(data, dict):
            import json
            payload = json.dumps(data).encode()
            opcode = OpCode.TEXT
        elif isinstance(data, str):
            payload = data.encode("utf-8")
            opcode = OpCode.TEXT
        else:
            payload = data
            opcode = OpCode.BINARY
        frame = WSFrame.build(opcode, payload)
        with self._send_lock:
            self.sock.sendall(frame)

    def listen(self):
        self._running = True
        buffer = bytearray()
        while self._running:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buffer.extend(chunk)
                while True:
                    result = WSFrame.parse(buffer)
                    if result is None:
                        break
                    fin, opcode, masked, length, payload, consumed = result
                    buffer = buffer[consumed:]
                    msg = self._process_frame(fin, opcode, payload)
                    if msg:
                        yield msg
            except Exception:
                break

    def _process_frame(self, fin: bool, opcode: int, payload: bytes) -> Optional[dict]:
        if opcode == OpCode.CLOSE:
            self._running = False
            return None
        if opcode == OpCode.PING:
            self.sock.sendall(WSFrame.build(OpCode.PONG, payload))
            return None
        if opcode == OpCode.PONG:
            return None
        if not fin:
            self._fragments.extend(payload)
            self._frag_type = opcode
            return None
        if self._fragments:
            self._fragments.extend(payload)
            payload = bytes(self._fragments)
            opcode = self._frag_type or opcode
            self._fragments = bytearray()
            self._frag_type = None
        if opcode == OpCode.TEXT:
            return {"type": "text", "data": payload.decode("utf-8")}
        elif opcode == OpCode.BINARY:
            return {"type": "binary", "data": bytes(payload)}
        return {"type": "unknown", "data": bytes(payload)}

    def close(self):
        self._running = False
        try:
            self.sock.sendall(WSFrame.build(OpCode.CLOSE, b""))
            self.sock.close()
        except Exception:
            pass
