from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from enum import Enum


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class HTTPVersion(Enum):
    HTTP11 = "HTTP/1.1"
    HTTP2 = "HTTP/2"


@dataclass
class HTTPHeader:
    name: str
    value: str

    def __post_init__(self):
        self.name = self.name.strip()
        self.value = self.value.strip()


@dataclass
class URLComponents:
    scheme: str
    host: str
    port: int
    path: str
    query: str = ""
    fragment: str = ""
    username: Optional[str] = None
    password: Optional[str] = None

    @property
    def netloc(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def origin(self) -> str:
        return f"{self.scheme}://{self.netloc}"

    @property
    def request_uri(self) -> str:
        uri = self.path or "/"
        if self.query:
            uri += f"?{self.query}"
        return uri


@dataclass
class ConnectionMetadata:
    created_at: float
    last_used: float = field(default=0.0)
    request_count: int = 0
    protocol: str = "http/1.1"
    stream_count: int = 0
    idle: bool = True

    @property
    def age(self) -> float:
        import time
        return time.time() - self.created_at

    @property
    def idle_time(self) -> float:
        import time
        return time.time() - self.last_used
