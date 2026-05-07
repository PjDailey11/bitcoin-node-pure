"""User-facing CLI helpers (validation, formatting, friendly errors)."""

from __future__ import annotations

import json
import re


_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


def normalize_hex(s: str) -> str:
    """Return lowercase hex with whitespace removed."""
    return "".join(s.split()).lower()


def decode_hex(s: str) -> bytes:
    hx = normalize_hex(s)
    if len(hx) == 0 or len(hx) % 2 != 0:
        raise ValueError("hex must have an even number of characters")
    if not _HEX_RE.match(hx):
        raise ValueError("hex contains non-hex characters")
    return bytes.fromhex(hx)


def txid_to_wire_le(txid_be_hex: str) -> str:
    """Explorer-style txid (big-endian hex) -> wire-order little-endian hex."""
    raw = decode_hex(txid_be_hex)
    if len(raw) != 32:
        raise ValueError("txid must be 32 bytes (64 hex chars)")
    return raw[::-1].hex()


def txid_from_wire_le(txid_le_hex: str) -> str:
    """Wire-order little-endian tx hash -> explorer-style big-endian hex."""
    raw = decode_hex(txid_le_hex)
    if len(raw) != 32:
        raise ValueError("txid must be 32 bytes (64 hex chars)")
    return raw[::-1].hex()


def print_json(obj: object) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))

