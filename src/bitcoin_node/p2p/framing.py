"""Bitcoin P2P message framing — magic, command, length, checksum."""

from __future__ import annotations

from bitcoin_node.crypto.sha256 import sha256d


def encode_message(magic: bytes, command: str, payload: bytes) -> bytes:
    cmd = command.encode("ascii")[:12]
    cmd = cmd + b"\x00" * (12 - len(cmd))
    chk = sha256d(payload)[:4]
    return magic + cmd + len(payload).to_bytes(4, "little") + chk + payload


def decode_message_header(data: bytes) -> tuple[str, int, bytes]:
    """Parse first 24 bytes — returns (command, payload_len, checksum4)."""
    if len(data) < 24:
        raise ValueError("short header")
    cmd = data[4:16].split(b"\x00", 1)[0].decode("ascii")
    ln = int.from_bytes(data[16:20], "little")
    chk = data[20:24]
    return cmd, ln, chk


def verify_payload_checksum(payload: bytes, chk: bytes) -> None:
    if sha256d(payload)[:4] != chk:
        raise ValueError("checksum mismatch")
