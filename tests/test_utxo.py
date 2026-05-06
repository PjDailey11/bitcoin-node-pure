from bitcoin_node.core.script import p2pkh_script_pubkey
from bitcoin_node.core.tx import Transaction, TxIn, TxOut
from bitcoin_node.core.utxo import Coin, OutPoint, UTXOSnapshot, apply_transaction, implicit_fee
from bitcoin_node.crypto.ripemd160 import hash160
from bitcoin_node.crypto.secp256k1 import parse_privkey, pubkey_bytes_compressed, pubkey_from_private


def _fund_view(value: int = 100_000_000) -> tuple[UTXOSnapshot, bytes, Coin]:
    priv = (987654321 % (0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141 - 2)) + 1
    priv_b = priv.to_bytes(32, "big")
    pub = pubkey_from_private(parse_privkey(priv_b))
    spk = p2pkh_script_pubkey(hash160(pubkey_bytes_compressed(pub)))

    coinbase = Transaction(1, tuple(), (TxOut(value, spk),), 0)
    view = UTXOSnapshot.empty()
    # bootstrap coin directly for brevity (avoid coinbase specifics)
    op = OutPoint(coinbase.txid(), 0)
    view = view.with_coin(op, Coin(value, spk))
    return view, coinbase.txid(), Coin(value, spk)


def test_fee_implicit() -> None:
    view, prev_txid, coin = _fund_view()
    fee = 10_000
    tx = Transaction(
        1,
        (TxIn(prev_txid, 0, b"", 0xFFFFFFFF),),
        (
            TxOut(coin.value - fee - 50_000_000, coin.script_pubkey),
            TxOut(50_000_000, coin.script_pubkey),
        ),
        0,
    )
    prevouts = {0: coin}
    new_view, mined_fee = apply_transaction(view, tx, prevouts)
    assert mined_fee == fee
    assert implicit_fee(prevouts, tx) == fee
    assert new_view.get(OutPoint(prev_txid, 0)) is None
    assert new_view.get(OutPoint(tx.txid(), 0)) is not None
