import base64


class BasicAuth:
    @staticmethod
    def header(username: str, password: str) -> str:
        creds = base64.b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {creds}"
