import hashlib
from typing import Dict, Optional
from .memory import MemoryCache
from .disk import DiskCache
from .policy import CachePolicy


class CacheManager:
    def __init__(self, memory_size: int = 100, disk_path: str = ".titanhttp_cache"):
        self.memory = MemoryCache(memory_size)
        self.disk = DiskCache(disk_path)

    def _key(self, method: str, url: str, vary_headers: Optional[Dict] = None) -> str:
        base = f"{method}:{url}"
        if vary_headers:
            base += ":" + str(sorted(vary_headers.items()))
        return hashlib.sha256(base.encode()).hexdigest()

    def get(self, method: str, url: str, request_headers: Dict[str, str]) -> Optional[dict]:
        key = self._key(method, url)
        entry = self.memory.get(key) or self.disk.get(key)
        if not entry:
            return None
        # Check Vary
        vary = entry.get("vary", [])
        for v in vary:
            if request_headers.get(v) != entry["request_headers"].get(v):
                return None
        return entry["response"]

    def store(self, method: str, url: str, request_headers: Dict[str, str], response: dict, response_headers: Dict[str, str]):
        if not CachePolicy.is_cacheable(method, response["status"], response_headers):
            return
        ttl = CachePolicy.ttl(response_headers)
        if ttl is None or ttl <= 0:
            return
        key = self._key(method, url)
        vary = response_headers.get("Vary", "")
        vary_list = [v.strip() for v in vary.split(",")] if vary else []
        entry = {
            "vary": vary_list,
            "request_headers": {v: request_headers.get(v) for v in vary_list},
            "response": response,
        }
        self.memory.set(key, entry, ttl)
        self.disk.set(key, entry, ttl)
