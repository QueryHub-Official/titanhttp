import time
from typing import Dict, List, Optional
from .parser import CookieParser
from .store import CookieStore


class CookieJar:
    def __init__(self, persist_file: Optional[str] = None):
        self._cookies: Dict[str, List[Dict]] = {}
        self._store = CookieStore(persist_file) if persist_file else None
        if self._store:
            self._store.load()
            self._cookies = self._store.all()

    def set_cookie(self, host: str, set_cookie: str):
        parsed = CookieParser.parse(set_cookie)
        if not parsed:
            return
        domain = parsed["domain"] or host
        if domain not in self._cookies:
            self._cookies[domain] = []
        # Remove existing with same name
        self._cookies[domain] = [c for c in self._cookies[domain] if c["name"] != parsed["name"]]
        self._cookies[domain].append(parsed)
        if self._store:
            self._store.set(domain, self._cookies[domain])

    def get_cookie_header(self, host: str, path: str) -> str:
        cookies = []
        now = time.time()
        for domain, jar in list(self._cookies.items()):
            if host == domain or (domain and host.endswith("." + domain)):
                valid = []
                for c in jar:
                    if not path.startswith(c.get("path", "/")):
                        continue
                    exp = c.get("expires")
                    if exp and exp < now:
                        continue
                    valid.append(c)
                    cookies.append(f"{c['name']}={c['value']}")
                self._cookies[domain] = valid
        return "; ".join(cookies)
