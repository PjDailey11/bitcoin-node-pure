"""Minimal Bitcoin script helpers (legacy P2PKH)."""

from __future__ import annotations

from bitcoin_node.core.varint import encode_compact_size

OP_DUP = 0x76
OP_HASH160 = 0xA9
OP_EQUALVERIFY = 0x88
OP_CHECKSIG = 0xAC


def push_bytes(data: bytes) -> bytes:
    n = len(data)
    if n < 76:
        return bytes([n]) + data
    if n < 256:
        return bytes([0x4C, n]) + data
    if n < 65536:
        return bytes([0x4D]) + n.to_bytes(2, "little") + data
    return bytes([0x4E]) + n.to_bytes(4, "little") + data


def p2pkh_script_pubkey(pubkey_hash20: bytes) -> bytes:
    if len(pubkey_hash20) != 20:
        raise ValueError("pubkey hash must be 20 bytes")
    return bytes([OP_DUP, OP_HASH160, 20]) + pubkey_hash20 + bytes([OP_EQUALVERIFY, OP_CHECKSIG])


def parse_p2pkh_script_pubkey(script: bytes) -> bytes | None:
    """Return pubkey hash if standard P2PKH or None."""
    if (
        len(script) == 25
        and script[0] == OP_DUP
        and script[1] == OP_HASH160
        and script[2] == 20
        and script[23] == OP_EQUALVERIFY
        and script[24] == OP_CHECKSIG
    ):
        return script[3:23]
    return None


def build_p2pkh_script_sig(sig_der: bytes, pubkey_compressed: bytes) -> bytes:
    return push_bytes(sig_der) + push_bytes(pubkey_compressed)


def script_serialize(script: bytes) -> bytes:
    return encode_compact_size(len(script)) + script


def read_push(script: bytes, offset: int = 0) -> tuple[bytes, int]:
    """Read pushed bytes after opcode; returns (data, next_offset)."""
    if offset >= len(script):
        raise ValueError("truncated script")
    op = script[offset]
    offset += 1
    if op < 76:
        ln = op
    elif op == 0x4C:
        if offset >= len(script):
            raise ValueError("truncated push")
        ln = script[offset]
        offset += 1
    elif op == 0x4D:
        ln = int.from_bytes(script[offset : offset + 2], "little")
        offset += 2
    elif op == 0x4E:
        ln = int.from_bytes(script[offset : offset + 4], "little")
        offset += 4
    else:
        raise ValueError(f"unsupported push opcode {op:#x}")
    end = offset + ln
    if end > len(script):
        raise ValueError("push exceeds script")
    return script[offset:end], end
