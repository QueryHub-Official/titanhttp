import time
import threading
from typing import Dict
from dataclasses import dataclass


@dataclass
class RateLimit:
    requests_per_second: float = 10.0
    burst: int = 5


class TokenBucketRateLimiter:
    def __init__(self, config: RateLimit):
        self.config = config
        self._tokens: Dict[str, float] = {}
        self._last: Dict[str, float] = {}
        self._lock = threading.Lock()

    def acquire(self, host: str):
        with self._lock:
            now = time.time()
            tokens = min(
                self.config.burst,
                self._tokens.get(host, self.config.burst)
                + (now - self._last.get(host, now)) * self.config.requests_per_second,
            )
            self._last[host] = now
            if tokens < 1:
                sleep = (1 - tokens) / self.config.requests_per_second
                time.sleep(sleep)
                tokens = 0
            else:
                tokens -= 1
            self._tokens[host] = tokens
