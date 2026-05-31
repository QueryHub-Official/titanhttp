import os
import time
from typing import Optional, Callable


class StreamDownloader:
    def __init__(self, client):
        self.client = client

    def download(
        self,
        url: str,
        path: str,
        resume: bool = False,
        throttle_kbps: Optional[int] = None,
        progress: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        headers = {}
        downloaded = 0
        if resume and os.path.exists(path):
            downloaded = os.path.getsize(path)
            headers["Range"] = f"bytes={downloaded}-"

        resp = self.client.get(url, headers=headers, stream=True)
        total = int(resp.headers.get("Content-Length", 0)) + downloaded

        mode = "ab" if resume and downloaded > 0 else "wb"
        with open(path, mode) as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)
                if throttle_kbps:
                    expected = len(chunk) / (throttle_kbps * 1024)
                    time.sleep(max(0, expected))
        return path
