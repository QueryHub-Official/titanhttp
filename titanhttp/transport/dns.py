import socket
import time
import threading
from typing import Dict, Tuple, List


class DNSCache:
    def __init__(self, default_ttl: float = 300.0, negative_ttl: float = 60.0):
        self.default_ttl = default_ttl
        self.negative_ttl = negative_ttl
        self._cache: Dict[str, Tuple[List[Tuple], float]] = {}
        self._lock = threading.Lock()

    def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET) -> Tuple:
        key = f"{host}:{port}:{family}"
        with self._lock:
            if key in self._cache:
                addrs, expiry = self._cache[key]
                if time.time() < expiry and addrs:
                    addr = addrs.pop(0)
                    addrs.append(addr)
                    return addr
        try:
            infos = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
            addrs = [info[4] for info in infos]
            with self._lock:
                self._cache[key] = (addrs, time.time() + self.default_ttl)
            return addrs[0]
        except socket.gaierror:
            with self._lock:
                self._cache[key] = ([], time.time() + self.negative_ttl)
            raise

    def clear(self):
        with self._lock:
            self._cache.clear()
