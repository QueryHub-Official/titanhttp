import time
from typing import Dict, Optional


class CookieParser:
    @staticmethod
    def parse(set_cookie: str) -> Optional[Dict]:
        parts = [p.strip() for p in set_cookie.split(";")]
        if not parts:
            return None
        kv = parts[0].split("=", 1)
        if len(kv) != 2:
            return None

        cookie = {
            "name": kv[0].strip(),
            "value": kv[1].strip(),
            "domain": "",
            "path": "/",
            "expires": None,
            "max_age": None,
            "secure": False,
            "httponly": False,
            "samesite": None,
        }

        for part in parts[1:]:
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if k == "domain":
                    cookie["domain"] = v.lstrip(".")
                elif k == "path":
                    cookie["path"] = v
                elif k == "expires":
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(v, "%a, %d %b %Y %H:%M:%S GMT")
                        cookie["expires"] = dt.timestamp()
                    except ValueError:
                        pass
                elif k == "max-age":
                    try:
                        cookie["max_age"] = int(v)
                    except ValueError:
                        pass
                elif k == "samesite":
                    cookie["samesite"] = v.lower()
            else:
                k = part.strip().lower()
                if k == "secure":
                    cookie["secure"] = True
                elif k == "httponly":
                    cookie["httponly"] = True
        return cookie
