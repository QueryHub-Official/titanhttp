import re
import time
from typing import Dict, Optional


class CachePolicy:
    """RFC 7234 cache policy parser."""

    @staticmethod
    def parse_cache_control(header: str) -> Dict[str, Optional[int]]:
        directives: Dict[str, Optional[int]] = {}
        if not header:
            return directives
        for part in header.split(","):
            part = part.strip().lower()
            if "=" in part:
                k, v = part.split("=", 1)
                try:
                    directives[k] = int(v)
                except ValueError:
                    directives[k] = None
            else:
                directives[part] = None
        return directives

    @staticmethod
    def is_cacheable(method: str, status: int, headers: Dict[str, str]) -> bool:
        if method not in ("GET", "HEAD"):
            return False
        cc = CachePolicy.parse_cache_control(headers.get("Cache-Control", ""))
        if "no-store" in cc:
            return False
        if "private" in cc and "public" not in cc:
            return False
        if status in (200, 203, 204, 206, 300, 301, 308, 404, 405, 410, 414, 501):
            return True
        return False

    @staticmethod
    def ttl(headers: Dict[str, str]) -> Optional[float]:
        cc = CachePolicy.parse_cache_control(headers.get("Cache-Control", ""))
        if "max-age" in cc:
            return cc["max-age"]
        if "s-maxage" in cc:
            return cc["s-maxage"]
        expires = headers.get("Expires")
        if expires:
            try:
                from datetime import datetime
                exp = datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S GMT")
                return max(0, (exp.timestamp() - time.time()))
            except ValueError:
                pass
        return None
