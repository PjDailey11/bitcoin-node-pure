import hashlib

from bitcoin_node.crypto.ripemd160 import hash160, ripemd160
from bitcoin_node.crypto.sha256 import sha256, sha256d


def test_sha256_vectors() -> None:
    assert sha256(b"abc").hex() == hashlib.sha256(b"abc").hexdigest()
    assert sha256d(b"x") == sha256(sha256(b"x"))


def test_ripemd160_vectors() -> None:
    assert ripemd160(b"").hex() == hashlib.new("ripemd160", b"").hexdigest()
    assert ripemd160(b"Rosetta Code").hex() == hashlib.new("ripemd160", b"Rosetta Code").hexdigest()


def test_hash160_pipeline() -> None:
    data = b"deadbeef"
    assert hash160(data) == ripemd160(sha256(data))
