"""DER encoding for ECDSA signatures (Bitcoin scriptSig format)."""

from __future__ import annotations


def _encode_integer(i: int) -> bytes:
    i = int(i)
    if i < 0:
        raise ValueError("negative DER integer")
    bl = i.to_bytes((i.bit_length() + 7) // 8 or 1, "big")
    if bl[0] & 0x80:
        bl = b"\x00" + bl
    return bytes([0x02, len(bl)]) + bl


def der_encode_ecdsa(r: int, s: int) -> bytes:
    """SEQUENCE { INTEGER r ; INTEGER s }."""
    body = _encode_integer(r) + _encode_integer(s)
    return bytes([0x30, len(body)]) + body


def der_decode_ecdsa(blob: bytes) -> tuple[int, int]:
    """Parse ECDSA DER signature."""
    if len(blob) < 6 or blob[0] != 0x30:
        raise ValueError("invalid DER signature")
    total_len = blob[1]
    inner = blob[2 : 2 + total_len]
    if blob[2] != 0x02:
        raise ValueError("expected INTEGER r")
    lr = inner[1]
    r_bytes = inner[2 : 2 + lr]
    pos = 2 + lr
    if inner[pos] != 0x02:
        raise ValueError("expected INTEGER s")
    ls = inner[pos + 1]
    s_bytes = inner[pos + 2 : pos + 2 + ls]
    r = int.from_bytes(r_bytes, "big")
    s = int.from_bytes(s_bytes, "big")
    return r, s
