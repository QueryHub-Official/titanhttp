import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any
from contextlib import contextmanager


class Recorder:
    def __init__(self, cassette_dir: str = ".titanhttp_cassettes"):
        self.dir = Path(cassette_dir)
        self.dir.mkdir(exist_ok=True)
        self._current: Optional[str] = None
        self._interactions: Dict[str, Any] = {}

    @contextmanager
    def use_cassette(self, name: str, mode: str = "once"):
        self._current = name
        self._interactions = {}
        path = self.dir / f"{name}.json"
        if mode in ("once", "replay") and path.exists():
            with open(path) as f:
                self._interactions = json.load(f)
        try:
            yield
        finally:
            if mode in ("once", "record"):
                with open(path, "w") as f:
                    json.dump(self._interactions, f)
            self._current = None

    def record(self, method: str, url: str, body: Optional[bytes], response: Any):
        key = self._key(method, url, body)
        self._interactions[key] = {
            "status": response.status,
            "headers": dict(response.headers),
            "content": response.content.decode("utf-8", errors="replace"),
            "url": response.url,
        }

    def replay(self, method: str, url: str, body: Optional[bytes]) -> Optional[Dict]:
        return self._interactions.get(self._key(method, url, body))

    def _key(self, method: str, url: str, body: Optional[bytes]) -> str:
        parts = [method, url]
        if body:
            parts.append(hashlib.sha256(body).hexdigest()[:16])
        return hashlib.sha256("|".join(parts).encode()).hexdigest()
