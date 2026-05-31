"""
TitanHTTP — Pure Python HTTP Arsenal
Zero dependencies. Python 3.10+ standard library only.
"""

__version__ = "2.0.0"

from .client.core import TitanClient
from .client.request import Request
from .client.response import Response
from .client.retry import RetryConfig
from .client.cache.manager import CacheManager
from .client.cookie.jar import CookieJar
from .client.proxy_rotator import ProxyRotator
from .utils.recorder import Recorder

__all__ = [
    "TitanClient",
    "Request",
    "Response",
    "RetryConfig",
    "CacheManager",
    "CookieJar",
    "ProxyRotator",
    "Recorder",
]
