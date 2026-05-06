import secrets

import pytest

from bitcoin_node.core.script import p2pkh_script_pubkey
from bitcoin_node.core.tx import (
    Transaction,
    TxIn,
    TxOut,
    parse_transaction,
    sign_p2pkh_input,
    verify_p2pkh_input,
)
from bitcoin_node.crypto.ripemd160 import hash160
from bitcoin_node.crypto.secp256k1 import parse_privkey, pubkey_bytes_compressed, pubkey_from_private


def _random_valid_priv() -> bytes:
    while True:
        priv = secrets.token_bytes(32)
        try:
            parse_privkey(priv)
            return priv
        except ValueError:
            continue


def test_p2pkh_sign_verify_roundtrip() -> None:
    priv = _random_valid_priv()
    pub = pubkey_from_private(parse_privkey(priv))
    pkh = hash160(pubkey_bytes_compressed(pub))
    spk = p2pkh_script_pubkey(pkh)

    prev_txid = bytes(range(32))
    tx = Transaction(1, (TxIn(prev_txid, 0, b"", 0xFFFFFFFF),), (TxOut(50_000_000 - 1000, spk),), 0)
    tx2 = sign_p2pkh_input(tx, 0, priv, spk)
    assert verify_p2pkh_input(tx2, 0, spk)
    raw = tx2.serialize()
    tx3, off = parse_transaction(raw)
    assert off == len(raw)
    assert tx3.serialize() == raw


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
