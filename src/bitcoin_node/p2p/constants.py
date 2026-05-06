"""Bitcoin P2P constants."""

from __future__ import annotations

MAINNET_MAGIC = bytes([0xF9, 0xBE, 0xB4, 0xD9])
TESTNET_MAGIC = bytes([0x0B, 0x11, 0x09, 0x07])

DEFAULT_MAINNET_PORT = 8333
DEFAULT_TESTNET_PORT = 18333

MSG_TX = 1
MSG_BLOCK = 2
