"""CLI entry — wallet keys and raw transaction relay."""

from __future__ import annotations

import argparse
import binascii
from pathlib import Path

from bitcoin_node.node import relay_raw_transaction_sync
from bitcoin_node.wallet import new_wallet_key


def _cmd_keys(_: argparse.Namespace) -> None:
    w = new_wallet_key()
    print("secret_hex:", w.secret_bytes.hex())
    print("pubkey_compressed_hex:", w.pubkey_compressed.hex())
    print("address_mainnet:", w.address_mainnet)
    print("address_testnet:", w.address_testnet)


def _cmd_broadcast(args: argparse.Namespace) -> None:
    if args.raw_hex:
        hx = args.raw_hex.strip()
    else:
        hx = Path(args.raw_file).read_text(encoding="utf-8").strip()
    raw = binascii.unhexlify(hx.replace(" ", ""))
    relay_raw_transaction_sync(args.network, raw, host=args.host, port=args.port)
    print(f"relayed {len(raw)} byte serialized transaction")


def main() -> None:
    p = argparse.ArgumentParser(description="bitcoin-node-pure educational CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    keys_p = sub.add_parser("keys", help="generate secp256k1 secret + legacy addresses")
    keys_p.set_defaults(func=_cmd_keys)

    bc = sub.add_parser("broadcast-tx", help="handshake with a peer and send a tx message")
    bc.add_argument("--network", choices=("mainnet", "testnet"), default="testnet")
    bc.add_argument("--host", help="skip DNS discovery")
    bc.add_argument("--port", type=int)
    g = bc.add_mutually_exclusive_group(required=True)
    g.add_argument("--raw-hex")
    g.add_argument("--raw-file", help="path containing hex serialized tx")
    bc.set_defaults(func=_cmd_broadcast)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
