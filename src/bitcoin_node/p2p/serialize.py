"""Minimal serializers for P2P payloads."""

from __future__ import annotations

import random
import struct
import time

from bitcoin_node.core.varint import encode_compact_size


def encode_var_str(s: bytes) -> bytes:
    return encode_compact_size(len(s)) + s


def encode_net_address(services: int, ipv4: bytes, port: int) -> bytes:
    if len(ipv4) != 4:
        raise ValueError("ipv4 must be 4 bytes")
    ipv6_mapped = b"\x00" * 10 + b"\xff\xff" + ipv4
    return services.to_bytes(8, "little") + ipv6_mapped + struct.pack(">H", port)


def build_version_payload(
    *,
    version: int = 70015,
    services: int = 1,
    timestamp: int | None = None,
    recv_addr: tuple[int, bytes, int] = (1, b"\x00\x00\x00\x00", 8333),
    from_addr: tuple[int, bytes, int] = (1, b"\x00\x00\x00\x00", 8333),
    nonce: int | None = None,
    user_agent: bytes = b"/bitcoin-node-pure:0.1/",
    start_height: int = 0,
    relay: bool = True,
) -> bytes:
    ts = int(time.time()) if timestamp is None else timestamp
    if nonce is None:
        nonce = random.getrandbits(64)
    rs, rip, rp = recv_addr
    fs, fip, fp = from_addr
    payload = b""
    payload += struct.pack("<i", version)
    payload += struct.pack("<Q", services)
    payload += struct.pack("<q", ts)
    payload += encode_net_address(rs, rip, rp)
    payload += encode_net_address(fs, fip, fp)
    payload += struct.pack("<Q", nonce)
    payload += encode_var_str(user_agent)
    payload += struct.pack("<i", start_height)
    payload += bytes([1 if relay else 0])
    return payload


def build_inv_tx_vector(tx_hashes: list[bytes]) -> bytes:
    """inv payload with MSG_TX entries."""
    if len(tx_hashes) > 50000:
        raise ValueError("inv too large")
    out = encode_compact_size(len(tx_hashes))
    for h in tx_hashes:
        if len(h) != 32:
            raise ValueError("tx hash must be 32 bytes wire-order")
        out += (1).to_bytes(4, "little") + h  # type MSG_TXLE - actually type is uint32 LE
    return out


def build_tx_payload(raw_tx: bytes) -> bytes:
    return raw_tx
