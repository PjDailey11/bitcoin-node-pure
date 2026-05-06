"""Legacy (non-segwit) Bitcoin transaction serialization + SIGHASH_ALL signing."""

from __future__ import annotations

from dataclasses import dataclass, replace

from bitcoin_node.core.script import build_p2pkh_script_sig, read_push
from bitcoin_node.core.varint import decode_compact_size, encode_compact_size
from bitcoin_node.crypto.der import der_decode_ecdsa, der_encode_ecdsa
from bitcoin_node.crypto.secp256k1 import (
    ecdsa_sign_digest,
    ecdsa_verify_digest,
    parse_privkey,
    pubkey_bytes_compressed,
    pubkey_from_private,
    pubkey_point_from_compressed,
)
from bitcoin_node.crypto.sha256 import sha256d


@dataclass(frozen=True)
class TxOut:
    value: int
    script_pubkey: bytes


@dataclass(frozen=True)
class TxIn:
    prev_txid: bytes  # 32 bytes wire-order (Bitcoin serialization uses LE tx hash)
    prev_index: int
    script_sig: bytes
    sequence: int = 0xFFFFFFFF


@dataclass(frozen=True)
class Transaction:
    version: int
    inputs: tuple[TxIn, ...]
    outputs: tuple[TxOut, ...]
    locktime: int = 0

    def serialize(self) -> bytes:
        out = self.version.to_bytes(4, "little")
        out += encode_compact_size(len(self.inputs))
        for tin in self.inputs:
            out += tin.prev_txid + tin.prev_index.to_bytes(4, "little")
            out += encode_compact_size(len(tin.script_sig)) + tin.script_sig
            out += tin.sequence.to_bytes(4, "little")
        out += encode_compact_size(len(self.outputs))
        for tout in self.outputs:
            out += tout.value.to_bytes(8, "little")
            out += encode_compact_size(len(tout.script_pubkey)) + tout.script_pubkey
        out += self.locktime.to_bytes(4, "little")
        return out

    def txid(self) -> bytes:
        """Binary txid (wire-order bytes). Explorers often display reversed hex."""
        return sha256d(self.serialize())


def clone_cleared_scripts(tx: Transaction) -> Transaction:
    cleared = tuple(replace(tin, script_sig=b"") for tin in tx.inputs)
    return Transaction(tx.version, cleared, tx.outputs, tx.locktime)


def legacy_sighash_all(tx: Transaction, input_index: int, script_code: bytes) -> bytes:
    """Legacy preimage for SIGHASH_ALL (type 1)."""
    if input_index < 0 or input_index >= len(tx.inputs):
        raise IndexError("input_index out of range")
    base = clone_cleared_scripts(tx)
    ins = list(base.inputs)
    cur = ins[input_index]
    ins[input_index] = replace(cur, script_sig=script_code)
    preimage_tx = Transaction(base.version, tuple(ins), base.outputs, base.locktime)
    preimage = preimage_tx.serialize() + (0x01).to_bytes(4, "little")
    return sha256d(preimage)


def parse_transaction(data: bytes, offset: int = 0) -> tuple[Transaction, int]:
    """Deserialize legacy transaction; returns (tx, next_offset)."""
    pos = offset
    version = int.from_bytes(data[pos : pos + 4], "little")
    pos += 4
    nin, pos = decode_compact_size(data, pos)
    inputs: list[TxIn] = []
    for _ in range(nin):
        prev_txid = data[pos : pos + 32]
        pos += 32
        prev_index = int.from_bytes(data[pos : pos + 4], "little")
        pos += 4
        slen, pos = decode_compact_size(data, pos)
        script_sig = data[pos : pos + slen]
        pos += slen
        sequence = int.from_bytes(data[pos : pos + 4], "little")
        pos += 4
        inputs.append(TxIn(prev_txid, prev_index, script_sig, sequence))

    nout, pos = decode_compact_size(data, pos)
    outputs: list[TxOut] = []
    for _ in range(nout):
        value = int.from_bytes(data[pos : pos + 8], "little")
        pos += 8
        plen, pos = decode_compact_size(data, pos)
        script_pubkey = data[pos : pos + plen]
        pos += plen
        outputs.append(TxOut(value, script_pubkey))

    locktime = int.from_bytes(data[pos : pos + 4], "little")
    pos += 4
    return Transaction(version, tuple(inputs), tuple(outputs), locktime), pos


def sign_p2pkh_input(
    tx: Transaction,
    input_index: int,
    privkey: bytes,
    prev_script_pubkey: bytes,
    sighash_type: int = 0x01,
) -> Transaction:
    """Return new tx with one input's scriptSig populated (SIGHASH_ALL only)."""
    if sighash_type != 0x01:
        raise NotImplementedError("only SIGHASH_ALL (0x01) supported")

    digest = legacy_sighash_all(tx, input_index, prev_script_pubkey)
    r, s = ecdsa_sign_digest(privkey, digest)
    der = der_encode_ecdsa(r, s)
    sig_blob = der + bytes([sighash_type])

    pub = pubkey_from_private(parse_privkey(privkey))
    pk_bytes = pubkey_bytes_compressed(pub)
    script_sig = build_p2pkh_script_sig(sig_blob, pk_bytes)

    ins = list(tx.inputs)
    ins[input_index] = replace(ins[input_index], script_sig=script_sig)
    return Transaction(tx.version, tuple(ins), tx.outputs, tx.locktime)


def verify_p2pkh_input(tx: Transaction, input_index: int, prev_script_pubkey: bytes) -> bool:
    """Structural verify for standard P2PKH spending known prev out."""
    tin = tx.inputs[input_index]
    pos = 0
    sig_der_with_type, pos = read_push(tin.script_sig, pos)
    pubkey_comp, pos = read_push(tin.script_sig, pos)
    if pos != len(tin.script_sig):
        return False
    if len(sig_der_with_type) < 2:
        return False
    sighash_type = sig_der_with_type[-1]
    if sighash_type != 0x01:
        return False
    der_blob = sig_der_with_type[:-1]
    try:
        r, s = der_decode_ecdsa(der_blob)
        pub = pubkey_point_from_compressed(pubkey_comp)
    except ValueError:
        return False

    digest = legacy_sighash_all(tx, input_index, prev_script_pubkey)
    return ecdsa_verify_digest(pub, digest, (r, s))
