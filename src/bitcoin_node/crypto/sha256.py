"""SHA-256 from scratch (padding + block schedule + rounds)."""

from __future__ import annotations

# Initial hash values (fractional parts of square roots of first 8 primes)
_H_INIT = (
    0x6A09E667,
    0xBB67AE85,
    0x3C6EF372,
    0xA54FF53A,
    0x510E527F,
    0x9B05688C,
    0x1F83D9AB,
    0x5BE0CD19,
)


# First 32 bits of fractional cube roots of first 64 primes (FIPS 180-4)
_K = (
    0x428A2F98,
    0x71374491,
    0xB5C0FBCF,
    0xE9B5DBA5,
    0x3956C25B,
    0x59F111F1,
    0x923F82A4,
    0xAB1C5ED5,
    0xD807AA98,
    0x12835B01,
    0x243185BE,
    0x550C7DC3,
    0x72BE5D74,
    0x80DEB1FE,
    0x9BDC06A7,
    0xC19BF174,
    0xE49B69C1,
    0xEFBE4786,
    0x0FC19DC6,
    0x240CA1CC,
    0x2DE92C6F,
    0x4A7484AA,
    0x5CB0A9DC,
    0x76F988DA,
    0x983E5152,
    0xA831C66D,
    0xB00327C8,
    0xBF597FC7,
    0xC6E00BF3,
    0xD5A79147,
    0x06CA6351,
    0x14292967,
    0x27B70A85,
    0x2E1B2138,
    0x4D2C6DFC,
    0x53380D13,
    0x650A7354,
    0x766A0ABB,
    0x81C2C92E,
    0x92722C85,
    0xA2BFE8A1,
    0xA81A664B,
    0xC24B8B70,
    0xC76C51A3,
    0xD192E819,
    0xD6990624,
    0xF40E3585,
    0x106AA070,
    0x19A4C116,
    0x1E376C08,
    0x2748774C,
    0x34B0BCB5,
    0x391C0CB3,
    0x4ED8AA4A,
    0x5B9CCA4F,
    0x682E6FF3,
    0x748F82EE,
    0x78A5636F,
    0x84C87814,
    0x8CC70208,
    0x90BEFFFA,
    0xA4506CEB,
    0xBEF9A3F7,
    0xC67178F2,
)


def _rotr(x: int, n: int) -> int:
    x &= 0xFFFFFFFF
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def _ch(x: int, y: int, z: int) -> int:
    x &= 0xFFFFFFFF
    return (x & y) ^ ((~x & 0xFFFFFFFF) & z & 0xFFFFFFFF)


def _maj(x: int, y: int, z: int) -> int:
    return (x & y) ^ (x & z) ^ (y & z)


def _sigma0(x: int) -> int:
    return _rotr(x, 2) ^ _rotr(x, 13) ^ _rotr(x, 22)


def _sigma1(x: int) -> int:
    return _rotr(x, 6) ^ _rotr(x, 11) ^ _rotr(x, 25)


def _gamma0(x: int) -> int:
    return _rotr(x, 7) ^ _rotr(x, 18) ^ (x >> 3)


def _gamma1(x: int) -> int:
    return _rotr(x, 17) ^ _rotr(x, 19) ^ (x >> 10)


def sha256_compress(block: bytes, state: tuple[int, ...]) -> tuple[int, ...]:
    """One 64-byte block."""
    assert len(block) == 64
    w = [0] * 64
    for i in range(16):
        w[i] = int.from_bytes(block[i * 4 : (i + 1) * 4], "big")
    for i in range(16, 64):
        w[i] = (_gamma1(w[i - 2]) + w[i - 7] + _gamma0(w[i - 15]) + w[i - 16]) & 0xFFFFFFFF

    a, b, c, d, e, f, g, h = state
    for i in range(64):
        t1 = (h + _sigma1(e) + _ch(e, f, g) + _K[i] + w[i]) & 0xFFFFFFFF
        t2 = (_sigma0(a) + _maj(a, b, c)) & 0xFFFFFFFF
        h, g, f, e, d, c, b, a = g, f, e, (d + t1) & 0xFFFFFFFF, c, b, a, (t1 + t2) & 0xFFFFFFFF

    return tuple((state[i] + (a, b, c, d, e, f, g, h)[i]) & 0xFFFFFFFF for i in range(8))


def sha256(message: bytes) -> bytes:
    """SHA-256 digest (32 bytes)."""
    ml = len(message) * 8
    pad_len = (56 - (len(message) + 1) % 64) % 64
    padded = message + b"\x80" + b"\x00" * pad_len + ml.to_bytes(8, "big")
    state = list(_H_INIT)
    for bi in range(0, len(padded), 64):
        state = list(sha256_compress(padded[bi : bi + 64], tuple(state)))
    return b"".join(x.to_bytes(4, "big") for x in state)


def sha256d(message: bytes) -> bytes:
    """Double SHA-256 (Bitcoin hash256)."""
    return sha256(sha256(message))
