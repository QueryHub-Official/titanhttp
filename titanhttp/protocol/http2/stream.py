from dataclasses import dataclass, field
from typing import Dict, Optional, Callable
from enum import Enum


class StreamState(Enum):
    IDLE = "idle"
    OPEN = "open"
    HALF_CLOSED_LOCAL = "half_closed_local"
    HALF_CLOSED_REMOTE = "half_closed_remote"
    CLOSED = "closed"


@dataclass
class HTTP2Stream:
    stream_id: int
    state: StreamState = field(default=StreamState.IDLE)
    request_headers: Dict[str, str] = field(default_factory=dict)
    response_headers: Dict[str, str] = field(default_factory=dict)
    data: bytearray = field(default_factory=bytearray)
    callback: Optional[Callable] = None

    def send_headers(self, headers: Dict[str, str], end_stream: bool = False):
        self.request_headers.update(headers)
        if end_stream:
            self.state = StreamState.HALF_CLOSED_LOCAL

    def receive_headers(self, headers: Dict[str, str], end_stream: bool = False):
        self.response_headers.update(headers)
        if end_stream:
            self.state = StreamState.HALF_CLOSED_REMOTE

    def receive_data(self, chunk: bytes, end_stream: bool = False):
        self.data.extend(chunk)
        if end_stream:
            self.state = StreamState.HALF_CLOSED_REMOTE

    def close(self):
        self.state = StreamState.CLOSED
