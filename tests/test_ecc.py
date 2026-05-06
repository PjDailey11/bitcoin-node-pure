from bitcoin_node.crypto.secp256k1 import (
    G,
    N,
    ecdsa_sign_digest,
    ecdsa_verify_digest,
    mod_inv,
    point_add,
    point_double,
    pubkey_bytes_compressed,
    pubkey_from_private,
    pubkey_point_from_compressed,
    scalar_mult,
)


def test_generator_order_and_identity() -> None:
    inf = scalar_mult(N, G)
    assert inf.is_infinity()


def test_compressed_roundtrip() -> None:
    pub = pubkey_from_private(1)
    comp = pubkey_bytes_compressed(pub)
    assert pubkey_point_from_compressed(comp).x == pub.x


def test_ecdsa_roundtrip() -> None:
    priv = (123456789 % (N - 2)) + 1  # keep valid-ish range without importing secrets loops
    priv_b = priv.to_bytes(32, "big")
    pub = pubkey_from_private(priv)
    msg_hash = bytes(range(32))
    r, s = ecdsa_sign_digest(priv_b, msg_hash)
    assert ecdsa_verify_digest(pub, msg_hash, (r, s))


def test_mod_inv() -> None:
    assert (7 * mod_inv(7, N)) % N == 1


def test_point_double_ADD() -> None:
    two_g = point_double(G)
    assert not two_g.is_infinity()
    three_g = point_add(G, two_g)
    assert not three_g.is_infinity()
