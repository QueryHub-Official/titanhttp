import time
import random
import threading
from typing import Dict
from dataclasses import dataclass
from ..exceptions import CircuitBreakerOpen, RetryExhausted


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True
    backoff_strategy: str = "exponential"  # exponential, fixed, decorrelated
    idempotent_methods: tuple = ("GET", "HEAD", "PUT", "DELETE", "OPTIONS", "PATCH")


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure = 0.0
        self.state = "CLOSED"
        self._lock = threading.Lock()

    def is_open(self) -> bool:
        with self._lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    return False
                return True
            return False

    def success(self):
        with self._lock:
            self.failures = 0
            self.state = "CLOSED"

    def failure(self):
        with self._lock:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"


class RetryController:
    def __init__(self, config: RetryConfig):
        self.config = config
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, host: str) -> CircuitBreaker:
        if host not in self._breakers:
            self._breakers[host] = CircuitBreaker()
        return self._breakers[host]

    def delay(self, attempt: int) -> float:
        if self.config.backoff_strategy == "fixed":
            base = self.config.base_delay
        elif self.config.backoff_strategy == "decorrelated":
            base = random.uniform(self.config.base_delay, self.config.max_delay)
        else:  # exponential
            base = self.config.base_delay * (2 ** attempt)
        capped = min(base, self.config.max_delay)
        if self.config.jitter:
            return random.uniform(0, capped)
        return capped

    def execute(self, host: str, func, *args, **kwargs):
        breaker = self.get_breaker(host)
        if breaker.is_open():
            raise CircuitBreakerOpen(f"Circuit breaker open for {host}")

        last_err = None
        for attempt in range(self.config.max_attempts):
            try:
                result = func(*args, **kwargs)
                breaker.success()
                return result
            except Exception as e:
                last_err = e
                breaker.failure()
                if attempt < self.config.max_attempts - 1:
                    time.sleep(self.delay(attempt))
        raise RetryExhausted(f"Failed after {self.config.max_attempts} attempts") from last_err
