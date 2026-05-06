"""Base58Check encoding (Bitcoin legacy addresses)."""

from __future__ import annotations

from bitcoin_node.crypto.sha256 import sha256d

_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode_raw(data: bytes) -> str:
    """Encode arbitrary bytes as Base58 (no checksum)."""
    n = int.from_bytes(data, "big")
    if n == 0:
        return _ALPHABET[0]
    out: list[str] = []
    while n > 0:
        n, rem = divmod(n, 58)
        out.append(_ALPHABET[rem])
    pad = 0
    for b in data:
        if b == 0:
            pad += 1
        else:
            break
    return _ALPHABET[0] * pad + "".join(reversed(out))


def b58decode_raw(s: str) -> bytes:
    """Decode Base58 string to bytes."""
    num = 0
    for ch in s:
        idx = _ALPHABET.index(ch)
        num = num * 58 + idx
    pad = 0
    for ch in s:
        if ch == _ALPHABET[0]:
            pad += 1
        else:
            break
    if num == 0:
        return b"\x00" * pad
    raw = num.to_bytes((num.bit_length() + 7) // 8, "big")
    return b"\x00" * pad + raw


def b58check_encode(version: int, payload: bytes) -> str:
    """version single byte + payload + 4-byte checksum."""
    vp = bytes([version]) + payload
    chk = sha256d(vp)[:4]
    return b58encode_raw(vp + chk)


def b58check_decode(s: str) -> tuple[int, bytes]:
    """Return (version, payload) after verifying checksum."""
    raw = b58decode_raw(s)
    if len(raw) < 5:
        raise ValueError("invalid Base58Check string")
    body, chk = raw[:-4], raw[-4:]
    if sha256d(body)[:4] != chk:
        raise ValueError("Base58Check checksum mismatch")
    return body[0], body[1:]
