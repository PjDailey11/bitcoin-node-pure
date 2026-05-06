"""Bitcoin CompactSize varints."""

from __future__ import annotations


def encode_compact_size(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative compact size")
    if n < 253:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + n.to_bytes(2, "little")
    if n <= 0xFFFFFFFF:
        return b"\xfe" + n.to_bytes(4, "little")
    return b"\xff" + n.to_bytes(8, "little")


def decode_compact_size(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Return (value, new_offset)."""
    if offset >= len(data):
        raise ValueError("truncated compact size")
    fb = data[offset]
    if fb < 253:
        return fb, offset + 1
    if fb == 0xFD:
        return int.from_bytes(data[offset + 1 : offset + 3], "little"), offset + 3
    if fb == 0xFE:
        return int.from_bytes(data[offset + 1 : offset + 5], "little"), offset + 5
    if fb == 0xFF:
        return int.from_bytes(data[offset + 1 : offset + 9], "little"), offset + 9
    raise ValueError("invalid compact size prefix")
