class TitanHTTPError(Exception):
    """Base exception."""
    pass


class ConnectionError(TitanHTTPError):
    pass


class ConnectTimeout(ConnectionError):
    pass


class ReadTimeout(ConnectionError):
    pass


class ProxyError(ConnectionError):
    pass


class TLSError(ConnectionError):
    pass


class ProtocolError(TitanHTTPError):
    pass


class HTTP2Error(ProtocolError):
    pass


class WebSocketError(ProtocolError):
    pass


class RetryExhausted(TitanHTTPError):
    pass


class CircuitBreakerOpen(TitanHTTPError):
    pass


class CacheError(TitanHTTPError):
    pass


class AuthError(TitanHTTPError):
    pass
