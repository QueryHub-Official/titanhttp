from .socks4 import SOCKS4
from .socks5 import SOCKS5


class SOCKSProxy:
    @staticmethod
    def connect_via_socks4(proxy_host: str, proxy_port: int, target_host: str, target_port: int):
        return SOCKS4.connect(proxy_host, proxy_port, target_host, target_port)

    @staticmethod
    def connect_via_socks5(
        proxy_host: str, proxy_port: int, target_host: str, target_port: int, username=None, password=None
    ):
        return SOCKS5.connect(proxy_host, proxy_port, target_host, target_port, username, password)
