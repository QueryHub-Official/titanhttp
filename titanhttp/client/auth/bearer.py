class BearerAuth:
    @staticmethod
    def header(token: str) -> str:
        return f"Bearer {token}"
