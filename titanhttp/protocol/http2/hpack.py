from typing import Dict, List, Tuple, Optional
from ...core.hpack_table import HPACKStaticTable


class HPACKDecoder:
    """Simplified HPACK decoder."""

    def __init__(self):
        self.dynamic_table: List[Tuple[str, str]] = []

    def decode(self, data: bytes) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        i = 0
        while i < len(data):
            b = data[i]
            if b & 0x80:
                # Indexed header
                index, i = self._decode_int(data, i, 7)
                entry = self._lookup(index)
                if entry:
                    headers[entry[0]] = entry[1]
            elif b & 0x40:
                # Literal with indexing
                index, i = self._decode_int(data, i, 6)
                name = self._name(index, data, i) if index > 0 else self._decode_string(data, i)
                value, i = self._decode_string(data, i + (len(name.encode()) if isinstance(name, str) else 0))
                if isinstance(name, bytes):
                    name = name.decode()
                if isinstance(value, bytes):
                    value = value.decode()
                headers[name] = value
                self.dynamic_table.insert(0, (name, value))
            elif b & 0x20:
                # Dynamic table size update
                _, i = self._decode_int(data, i, 5)
            else:
                # Literal without indexing / never indexed
                index, i = self._decode_int(data, i, 4)
                name = self._name(index, data, i) if index > 0 else self._decode_string(data, i)
                value, i = self._decode_string(data, i + (len(name.encode()) if isinstance(name, str) else 0))
                if isinstance(name, bytes):
                    name = name.decode()
                if isinstance(value, bytes):
                    value = value.decode()
                headers[name] = value
        return headers

    def _decode_int(self, data: bytes, i: int, prefix_bits: int) -> Tuple[int, int]:
        mask = (1 << prefix_bits) - 1
        value = data[i] & mask
        i += 1
        if value == mask:
            m = 0
            while True:
                b = data[i]
                value += (b & 0x7F) << m
                m += 7
                i += 1
                if not (b & 0x80):
                    break
        return value, i

    def _decode_string(self, data: bytes, i: int) -> Tuple[str, int]:
        huffman = bool(data[i] & 0x80)
        length, i = self._decode_int(data, i, 7)
        s = data[i : i + length]
        if huffman:
            # Simplified: treat as literal (real implementation needs Huffman tree)
            s = s.decode("latin1")
        else:
            s = s.decode()
        return s, i + length

    def _lookup(self, index: int) -> Optional[Tuple[str, str]]:
        static_len = len(HPACKStaticTable.TABLE)
        if index <= static_len:
            return HPACKStaticTable.lookup(index)
        elif index <= static_len + len(self.dynamic_table):
            return self.dynamic_table[index - static_len - 1]
        return None

    def _name(self, index: int, data: bytes, i: int):
        entry = self._lookup(index)
        if entry:
            return entry[0]
        return self._decode_string(data, i)


class HPACEncoder:
    """Simplified HPACK encoder (literal only, no huffman)."""

    def __init__(self):
        self.dynamic_table: List[Tuple[str, str]] = []

    def encode(self, headers: Dict[str, str]) -> bytes:
        result = bytearray()
        for k, v in headers.items():
            key = k.lower()
            # Literal header field, new name (0x40)
            key_bytes = key.encode()
            val_bytes = v.encode()
            result.append(0x40 | (len(key_bytes) & 0x3F))
            result.extend(key_bytes)
            result.append(len(val_bytes) & 0x7F)
            result.extend(val_bytes)
        return bytes(result)
