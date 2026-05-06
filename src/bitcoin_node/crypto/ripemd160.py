"""RIPEMD-160 — pure Python (Rosetta Code / standard word-wise formulation)."""

from __future__ import annotations

MASK = 0xFFFFFFFF


def _rol(value: int, shift: int) -> int:
    value &= MASK
    return ((value << shift) | (value >> (32 - shift))) & MASK


def _f0(x: int, y: int, z: int) -> int:
    return x ^ y ^ z


def _f1(x: int, y: int, z: int) -> int:
    return (x & y) | ((~x & MASK) & z)


def _f2(x: int, y: int, z: int) -> int:
    return (x | (~y & MASK)) ^ z


def _f3(x: int, y: int, z: int) -> int:
    return (x & z) | (y & (~z & MASK))


def _f4(x: int, y: int, z: int) -> int:
    return x ^ (y | (~z & MASK))


_FL = (_f0, _f1, _f2, _f3, _f4)

_K = (0x00000000, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E)
_KK = (0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0x00000000)

_R = (
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    7,
    4,
    13,
    1,
    10,
    6,
    15,
    3,
    12,
    0,
    9,
    5,
    2,
    14,
    11,
    8,
    3,
    10,
    14,
    4,
    9,
    15,
    8,
    1,
    2,
    7,
    0,
    6,
    13,
    11,
    5,
    12,
    1,
    9,
    11,
    10,
    0,
    8,
    12,
    4,
    13,
    3,
    7,
    15,
    14,
    5,
    6,
    2,
    4,
    0,
    5,
    9,
    7,
    12,
    2,
    10,
    14,
    1,
    3,
    8,
    11,
    6,
    15,
    13,
)

_RR = (
    5,
    14,
    7,
    0,
    9,
    2,
    11,
    4,
    13,
    6,
    15,
    8,
    1,
    10,
    3,
    12,
    6,
    11,
    3,
    7,
    0,
    13,
    5,
    10,
    14,
    15,
    8,
    12,
    4,
    9,
    1,
    2,
    15,
    5,
    1,
    3,
    7,
    14,
    6,
    9,
    11,
    8,
    12,
    2,
    10,
    0,
    4,
    13,
    8,
    6,
    4,
    1,
    3,
    11,
    15,
    0,
    5,
    12,
    2,
    13,
    9,
    7,
    10,
    14,
    12,
    15,
    10,
    4,
    1,
    5,
    8,
    7,
    6,
    2,
    13,
    14,
    0,
    3,
    9,
    11,
)

_S = (
    11,
    14,
    15,
    12,
    5,
    8,
    7,
    9,
    11,
    13,
    14,
    15,
    6,
    7,
    9,
    8,
    7,
    6,
    8,
    13,
    11,
    9,
    7,
    15,
    7,
    12,
    15,
    9,
    11,
    7,
    13,
    12,
    11,
    13,
    6,
    7,
    14,
    9,
    13,
    15,
    14,
    8,
    13,
    6,
    5,
    12,
    7,
    5,
    11,
    12,
    14,
    15,
    14,
    15,
    9,
    8,
    9,
    14,
    5,
    6,
    8,
    6,
    5,
    12,
    9,
    15,
    5,
    11,
    6,
    8,
    13,
    12,
    5,
    12,
    13,
    14,
    11,
    8,
    5,
    6,
)

_SS = (
    8,
    9,
    9,
    11,
    13,
    15,
    15,
    5,
    7,
    7,
    8,
    11,
    14,
    14,
    12,
    6,
    9,
    13,
    15,
    7,
    12,
    8,
    9,
    11,
    7,
    7,
    12,
    7,
    6,
    15,
    13,
    11,
    9,
    7,
    15,
    11,
    8,
    6,
    6,
    14,
    12,
    13,
    5,
    14,
    13,
    13,
    7,
    5,
    15,
    5,
    8,
    11,
    14,
    14,
    6,
    14,
    6,
    9,
    12,
    9,
    12,
    5,
    15,
    8,
    8,
    5,
    12,
    9,
    12,
    5,
    14,
    6,
    8,
    13,
    6,
    5,
    15,
    13,
    11,
    11,
)


def ripemd160_compress(chunk: bytes, state: tuple[int, int, int, int, int]) -> tuple[int, int, int, int, int]:
    """Single 64-byte block."""
    assert len(chunk) == 64
    x = [int.from_bytes(chunk[4 * i : 4 * i + 4], "little") for i in range(16)]

    h0, h1, h2, h3, h4 = state
    a, b, c, d, e = h0, h1, h2, h3, h4
    aa, bb, cc, dd, ee = h0, h1, h2, h3, h4

    j = 0
    for ro in range(5):
        fl = _FL[ro]
        fr = _FL[4 - ro]
        kl = _K[ro]
        kr = _KK[ro]
        for _ in range(16):
            ol_a, ol_b, ol_c, ol_d, ol_e = a, b, c, d, e
            oa_a, oa_b, oa_c, oa_d, oa_e = aa, bb, cc, dd, ee

            a = ol_e
            e = ol_d
            d = _rol(ol_c, 10)
            c = ol_b
            b = (_rol(ol_a + fl(ol_b, ol_c, ol_d) + x[_R[j]] + kl, _S[j]) + ol_e) & MASK

            aa = oa_e
            ee = oa_d
            dd = _rol(oa_c, 10)
            cc = oa_b
            bb = (_rol(oa_a + fr(oa_b, oa_c, oa_d) + x[_RR[j]] + kr, _SS[j]) + oa_e) & MASK

            j += 1

    s0 = (h1 + c + dd) & MASK
    s1 = (h2 + d + ee) & MASK
    s2 = (h3 + e + aa) & MASK
    s3 = (h4 + a + bb) & MASK
    s4 = (h0 + b + cc) & MASK
    return (s0, s1, s2, s3, s4)


def ripemd160(message: bytes) -> bytes:
    """RIPEMD-160 digest (20 bytes)."""
    ml_bits = len(message) * 8
    pad_len = (64 - (len(message) + 1 + 8) % 64) % 64
    padded = message + b"\x80" + b"\x00" * pad_len + ml_bits.to_bytes(8, "little")

    state = (
        0x67452301,
        0xEFCDAB89,
        0x98BADCFE,
        0x10325476,
        0xC3D2E1F0,
    )
    for bi in range(0, len(padded), 64):
        state = ripemd160_compress(padded[bi : bi + 64], state)
    return b"".join(w.to_bytes(4, "little") for w in state)


def hash160(data: bytes) -> bytes:
    """Bitcoin HASH160: RIPEMD160(SHA256(data))."""
    from bitcoin_node.crypto.sha256 import sha256

    return ripemd160(sha256(data))
