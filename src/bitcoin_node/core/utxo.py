"""Immutable UTXO snapshots — deterministic fee accounting."""

from __future__ import annotations

from dataclasses import dataclass

from bitcoin_node.core.tx import Transaction


@dataclass(frozen=True)
class OutPoint:
    txid: bytes  # 32-byte wire-order hash from Transaction.txid()
    index: int


@dataclass(frozen=True)
class Coin:
    value: int
    script_pubkey: bytes


@dataclass(frozen=True)
class UTXOSnapshot:
    """Frozen mapping keyed by OutPoint."""

    _table: dict[OutPoint, Coin]

    @classmethod
    def empty(cls) -> UTXOSnapshot:
        return cls({})

    def clone(self) -> UTXOSnapshot:
        return UTXOSnapshot(dict(self._table))

    def get(self, op: OutPoint) -> Coin | None:
        return self._table.get(op)

    def with_coin(self, op: OutPoint, coin: Coin) -> UTXOSnapshot:
        d = dict(self._table)
        d[op] = coin
        return UTXOSnapshot(d)

    def without(self, op: OutPoint) -> UTXOSnapshot:
        d = dict(self._table)
        if op in d:
            del d[op]
        return UTXOSnapshot(d)


def apply_coinbase(tx: Transaction, view: UTXOSnapshot) -> UTXOSnapshot:
    """Mint outputs from a coinbase / genesis funding tx into the view."""
    txid = tx.txid()
    out = view
    for idx, vo in enumerate(tx.outputs):
        op = OutPoint(txid, idx)
        out = out.with_coin(op, Coin(vo.value, vo.script_pubkey))
    return out


def apply_transaction(
    view: UTXOSnapshot,
    tx: Transaction,
    prevouts: dict[int, Coin],
) -> tuple[UTXOSnapshot, int]:
    """Spend inputs listed in prevouts (input_index -> coin). Returns (new_view, fee).

    prevouts must reference coins currently present in **view** unless modelling CPFP separately.
    """

    # Validate spends exist and amounts cover outputs
    total_in = 0
    tmp = view.clone()
    for idx, tin in enumerate(tx.inputs):
        coin = prevouts.get(idx)
        if coin is None:
            raise ValueError(f"missing prevout for input {idx}")
        op = OutPoint(tin.prev_txid, tin.prev_index)
        cur = tmp.get(op)
        if cur is None:
            raise ValueError(f"UTXO not found for input {idx}")
        if cur.value != coin.value or cur.script_pubkey != coin.script_pubkey:
            raise ValueError("prevout descriptor mismatch")
        total_in += cur.value
        tmp = tmp.without(op)

    total_out = sum(o.value for o in tx.outputs)
    if total_out > total_in:
        raise ValueError("outputs exceed inputs")

    fee = total_in - total_out

    # Append new outputs
    txid = tx.txid()
    for idx, vo in enumerate(tx.outputs):
        tmp = tmp.with_coin(OutPoint(txid, idx), Coin(vo.value, vo.script_pubkey))

    return tmp, fee


def implicit_fee(prevouts: dict[int, Coin], tx: Transaction) -> int:
    """Fee from explicit prevout values minus outputs (no UTXO mutation)."""
    total_in = sum(c.value for c in prevouts.values())
    total_out = sum(o.value for o in tx.outputs)
    return total_in - total_out
