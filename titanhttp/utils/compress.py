import zlib


def decompress(data: bytes, encoding: str) -> bytes:
    enc = encoding.lower().strip()
    if enc == "gzip":
        return zlib.decompress(data, 16 + zlib.MAX_WBITS)
    elif enc == "deflate":
        try:
            return zlib.decompress(data, -zlib.MAX_WBITS)
        except zlib.error:
            return zlib.decompress(data)
    return data
