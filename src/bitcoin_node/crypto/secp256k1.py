"""secp256k1 affine arithmetic + ECDSA (Bitcoin low-S, RFC6979 deterministic k)."""

from __future__ import annotations

from dataclasses import dataclass

from bitcoin_node.crypto.sha256 import sha256

P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def _mod(a: int, m: int) -> int:
    return a % m


def mod_inv(a: int, m: int) -> int:
    """Extended Euclidean algorithm — modular inverse of a modulo m."""
    a %= m
    if a == 0:
        raise ZeroDivisionError("no inverse")
    old_r, r = a, m
    old_s, s = 1, 0
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
    return old_s % m


@dataclass(frozen=True)
class Point:
    """Affine point; infinity when x and y are None."""

    x: int | None
    y: int | None

    def is_infinity(self) -> bool:
        return self.x is None


INF = Point(None, None)
G = Point(GX, GY)


def point_add(a: Point, b: Point) -> Point:
    if a.is_infinity():
        return b
    if b.is_infinity():
        return a
    assert a.x is not None and a.y is not None and b.x is not None and b.y is not None
    if a.x == b.x:
        if (a.y + b.y) % P == 0:
            return INF
        return point_double(a)
    lam = _mod((b.y - a.y) * mod_inv(b.x - a.x, P), P)
    x3 = _mod(lam * lam - a.x - b.x, P)
    y3 = _mod(lam * (a.x - x3) - a.y, P)
    return Point(x3, y3)


def point_double(a: Point) -> Point:
    if a.is_infinity():
        return INF
    assert a.x is not None and a.y is not None
    if a.y % P == 0:
        return INF
    lam = _mod((3 * a.x * a.x) * mod_inv(2 * a.y, P), P)
    x3 = _mod(lam * lam - 2 * a.x, P)
    y3 = _mod(lam * (a.x - x3) - a.y, P)
    return Point(x3, y3)


def scalar_mult(k: int, pt: Point) -> Point:
    """Double-and-add."""
    if k % N == 0 or pt.is_infinity():
        return INF
    acc = INF
    addend = pt
    kk = k % N
    while kk > 0:
        if kk & 1:
            acc = point_add(acc, addend)
        addend = point_double(addend)
        kk >>= 1
    return acc


def pubkey_from_private(d: int) -> Point:
    return scalar_mult(d % N, G)


def pubkey_bytes_compressed(pub: Point) -> bytes:
    if pub.is_infinity():
        raise ValueError("cannot serialize infinity")
    assert pub.x is not None and pub.y is not None
    prefix = 0x02 if pub.y % 2 == 0 else 0x03
    return bytes([prefix]) + pub.x.to_bytes(32, "big")


def pubkey_point_from_compressed(data: bytes) -> Point:
    """Decode compressed SEC pubkey (33 bytes) to affine point."""
    if len(data) != 33 or data[0] not in (0x02, 0x03):
        raise ValueError("invalid compressed pubkey")
    x = int.from_bytes(data[1:], "big")
    rhs = _mod(pow(x, 3, P) + 7, P)
    y = pow(rhs, (P + 1) // 4, P)
    if pow(y, 2, P) != rhs:
        raise ValueError("invalid pubkey coordinate")
    if y % 2 != (data[0] & 1):
        y = P - y
    return Point(x, y)


def pubkey_bytes_uncompressed(pub: Point) -> bytes:
    if pub.is_infinity():
        raise ValueError("cannot serialize infinity")
    assert pub.x is not None and pub.y is not None
    return b"\x04" + pub.x.to_bytes(32, "big") + pub.y.to_bytes(32, "big")


def parse_privkey(secret: bytes) -> int:
    if len(secret) != 32:
        raise ValueError("private key must be 32 bytes")
    d = int.from_bytes(secret, "big")
    if d <= 0 or d >= N:
        raise ValueError("private key out of range")
    return d


def _bits2int(b: bytes) -> int:
    return int.from_bytes(b, "big")


def _hmac_sha256(key: bytes, msg: bytes) -> bytes:
    block = 64
    if len(key) > block:
        key = sha256(key)
    key = key + b"\x00" * (block - len(key))
    ipad = bytes(x ^ 0x36 for x in key)
    opad = bytes(x ^ 0x5C for x in key)
    return sha256(opad + sha256(ipad + msg))


def generate_k_rfc6979(secret: bytes, h1: bytes) -> int:
    """RFC6979 deterministic nonce for secp256k1-SHA256."""
    qlen = N.bit_length()
    holen = len(h1) * 8
    if holen < qlen:
        raise ValueError("hash length insufficient")

    x = secret
    k_bytestrlen = (qlen + 7) // 8

    hlen = 256 // 8
    v = b"\x01" * hlen
    kk = b"\x00" * hlen

    kk = _hmac_sha256(kk, v + b"\x00" + x + h1)
    v = _hmac_sha256(kk, v)
    kk = _hmac_sha256(kk, v + b"\x01" + x + h1)
    v = _hmac_sha256(kk, v)

    while True:
        t = b""
        while len(t) * 8 < qlen:
            v = _hmac_sha256(kk, v)
            t += v
        k_candidate = _bits2int(t[:k_bytestrlen])
        if k_candidate >= 1 and k_candidate < N:
            return k_candidate
        kk = _hmac_sha256(kk, v + b"\x00")
        v = _hmac_sha256(kk, v)


def _low_s(s: int) -> int:
    half_n = N // 2
    if s > half_n:
        return N - s
    return s


def ecdsa_sign_digest(priv_bytes: bytes, digest32: bytes) -> tuple[int, int]:
    """Sign *digest32* (already hashed message). Returns (r, s) integers."""
    d = parse_privkey(priv_bytes)
    z = int.from_bytes(digest32, "big") % N
    if z == 0:
        z = 1

    k = generate_k_rfc6979(priv_bytes, digest32)
    kinv = mod_inv(k, N)
    r_pt = scalar_mult(k, G)
    if r_pt.is_infinity():
        raise RuntimeError("unexpected infinity during signing")
    assert r_pt.x is not None
    r = r_pt.x % N
    if r == 0:
        raise RuntimeError("retry signing — r == 0")

    s = _mod(kinv * (z + r * d), N)
    if s == 0:
        raise RuntimeError("retry signing — s == 0")
    s = _low_s(s)
    return r, s


def ecdsa_verify_digest(pub: Point, digest32: bytes, sig: tuple[int, int]) -> bool:
    z = int.from_bytes(digest32, "big") % N
    r, s = sig
    if r <= 0 or r >= N or s <= 0 or s >= N:
        return False
    w = mod_inv(s, N)
    u1 = _mod(z * w, N)
    u2 = _mod(r * w, N)
    pt = point_add(scalar_mult(u1, G), scalar_mult(u2, pub))
    if pt.is_infinity():
        return False
    assert pt.x is not None
    return (pt.x % N) == r
