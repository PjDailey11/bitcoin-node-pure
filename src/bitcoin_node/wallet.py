"""Wallet utilities — random keys and legacy P2PKH addresses."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from bitcoin_node.core.script import p2pkh_script_pubkey
from bitcoin_node.crypto.base58 import b58check_encode
from bitcoin_node.crypto.ripemd160 import hash160
from bitcoin_node.crypto.secp256k1 import parse_privkey, pubkey_bytes_compressed, pubkey_from_private

VERSION_MAINNET = 0x00
VERSION_TESTNET = 0x6F


@dataclass(frozen=True)
class WalletKey:
    secret_bytes: bytes
    pubkey_compressed: bytes
    address_mainnet: str
    address_testnet: str

    def p2pkh_script_pubkey(self) -> bytes:
        return p2pkh_script_pubkey(hash160(self.pubkey_compressed))


def new_wallet_key() -> WalletKey:
    while True:
        secret = secrets.token_bytes(32)
        try:
            d = parse_privkey(secret)
            break
        except ValueError:
            continue
    pub_pt = pubkey_from_private(d)
    pkc = pubkey_bytes_compressed(pub_pt)
    h = hash160(pkc)
    return WalletKey(
        secret,
        pkc,
        b58check_encode(VERSION_MAINNET, h),
        b58check_encode(VERSION_TESTNET, h),
    )
