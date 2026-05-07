"""CLI entry — wallet keys and raw transaction relay."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from bitcoin_node.cli_helpers import (
    decode_hex,
    print_json,
    txid_from_wire_le,
    txid_to_wire_le,
)
from bitcoin_node.node import relay_raw_transaction_sync
from bitcoin_node.p2p.dns_seeds import gather_peers
from bitcoin_node.core.tx import parse_transaction
from bitcoin_node.crypto.sha256 import sha256d
from bitcoin_node.version import __version__
from bitcoin_node.wallet import VERSION_MAINNET, VERSION_TESTNET, new_wallet_key
from bitcoin_node.crypto.base58 import b58check_encode
from bitcoin_node.crypto.ripemd160 import hash160
from bitcoin_node.crypto.secp256k1 import parse_privkey, pubkey_bytes_compressed, pubkey_from_private


def _cmd_keys(args: argparse.Namespace) -> None:
    w = new_wallet_key()
    payload = {
        "secret_hex": None if args.no_secret else w.secret_bytes.hex(),
        "pubkey_compressed_hex": w.pubkey_compressed.hex(),
        "address_mainnet": w.address_mainnet,
        "address_testnet": w.address_testnet,
    }
    if args.format == "json" or args.out:
        rendered = json.dumps(payload, indent=2, sort_keys=True)
        if args.out:
            Path(args.out).write_text(rendered + "\n", encoding="utf-8")
            if args.format != "quiet":
                print(f"wrote: {args.out}")
            return
        print(rendered)
        return
    if args.format == "quiet":
        return
    print("secret_hex:", payload["secret_hex"])
    print("pubkey_compressed_hex:", payload["pubkey_compressed_hex"])
    print("address_mainnet:", payload["address_mainnet"])
    print("address_testnet:", payload["address_testnet"])


def _cmd_broadcast(args: argparse.Namespace) -> None:
    if args.list_peers:
        peers = _run_async_gather_peers(args.network, args.peer_limit)
        for i, (h, p) in enumerate(peers):
            print(f"[{i}] {h}:{p}")
        return

    if not args.raw_hex and not args.raw_file:
        if args.raw_stdin:
            hx = sys.stdin.read()
            raw = decode_hex(hx)
        else:
            raise SystemExit("provide --raw-hex, --raw-file, or --raw-stdin (or use --list-peers)")
    else:
        if args.raw_hex:
            hx = args.raw_hex
        else:
            hx = Path(args.raw_file).read_text(encoding="utf-8")
        raw = decode_hex(hx)

    host = args.host
    port = args.port
    if host is None and args.peer_index is not None:
        peers = _run_async_gather_peers(args.network, max(args.peer_limit, args.peer_index + 1))
        if args.peer_index >= len(peers):
            raise SystemExit(f"--peer-index {args.peer_index} is out of range (got {len(peers)} peers)")
        host, port = peers[args.peer_index]

    if args.dry_run:
        print(f"dry-run: would connect to {host or '<dns-seed>'} on {args.network} and send {len(raw)} bytes")
        print("tip: run `btc-pure broadcast-tx --list-peers` to see which peer index you are using")
        return

    relay_raw_transaction_sync(
        args.network,
        raw,
        host=host,
        port=port,
        timeout=args.timeout,
        dry_run=False,
    )
    print(f"sent {len(raw)} byte serialized transaction (best-effort)")


def _run_async_gather_peers(network: str, limit: int) -> list[tuple[str, int]]:
    import asyncio

    return asyncio.run(gather_peers(network, limit=limit))


def _cmd_txid(args: argparse.Namespace) -> None:
    if args.direction == "to-wire":
        print(txid_to_wire_le(args.txid_hex))
    else:
        print(txid_from_wire_le(args.txid_hex))


def _cmd_validate_hex(args: argparse.Namespace) -> None:
    try:
        b = decode_hex(args.hex)
    except ValueError as e:
        raise SystemExit(f"invalid hex: {e}") from e
    print(f"ok: {len(b)} bytes")


def _cmd_doctor(args: argparse.Namespace) -> None:
    print("bitcoin-node-pure doctor")
    print("version:", __version__)
    print("python:", sys.version.split()[0], f"({platform.platform()})")
    print("network:", args.network)
    peers = _run_async_gather_peers(args.network, args.peer_limit)
    if not peers:
        raise SystemExit("dns: no peers returned (try --network testnet or pass --host/--port)")
    print(f"dns: resolved {len(peers)} peers (showing up to {min(5, len(peers))})")
    for h, p in peers[:5]:
        print(" -", f"{h}:{p}")
    print("ok")

def _cmd_address(args: argparse.Namespace) -> None:
    if args.secret_hex:
        priv = decode_hex(args.secret_hex)
        d = parse_privkey(priv)
        pub = pubkey_from_private(d)
        pubc = pubkey_bytes_compressed(pub)
    else:
        pubc = decode_hex(args.pubkey_hex)
        if len(pubc) != 33 or pubc[0] not in (2, 3):
            raise SystemExit("pubkey must be 33-byte compressed SEC (starts with 02 or 03)")

    h160 = hash160(pubc)
    addr_main = b58check_encode(VERSION_MAINNET, h160)
    addr_test = b58check_encode(VERSION_TESTNET, h160)

    if args.network == "mainnet":
        print(addr_main)
    elif args.network == "testnet":
        print(addr_test)
    else:
        print("address_mainnet:", addr_main)
        print("address_testnet:", addr_test)


def _cmd_tx_decode(args: argparse.Namespace) -> None:
    raw = decode_hex(args.raw_hex) if args.raw_hex else decode_hex(Path(args.raw_file).read_text(encoding="utf-8"))
    tx, off = parse_transaction(raw)
    if off != len(raw):
        raise SystemExit(f"tx parse ended early at {off}/{len(raw)} bytes (non-legacy or trailing data?)")
    txid_le = sha256d(raw)
    txid_be = txid_le[::-1].hex()

    summary = {
        "bytes": len(raw),
        "txid_be": txid_be,
        "txid_le": txid_le.hex(),
        "version": tx.version,
        "inputs": len(tx.inputs),
        "outputs": len(tx.outputs),
        "locktime": tx.locktime,
        "outputs_sats": [o.value for o in tx.outputs],
    }
    if args.format == "json":
        print_json(summary)
    else:
        print("bytes:", summary["bytes"])
        print("txid (explorer / big-endian):", summary["txid_be"])
        print("txid (wire / little-endian):", summary["txid_le"])
        print("version:", summary["version"])
        print("inputs:", summary["inputs"])
        print("outputs:", summary["outputs"])
        print("locktime:", summary["locktime"])
        print("outputs (sats):", summary["outputs_sats"])


def main() -> None:
    p = argparse.ArgumentParser(
        prog="btc-pure",
        description="bitcoin-node-pure educational CLI",
        epilog=(
            "Examples:\n"
            "  btc-pure keys\n"
            "  btc-pure doctor --network testnet\n"
            "  btc-pure txid to-wire <explorer-txid-hex>\n"
            "  btc-pure broadcast-tx --network testnet --list-peers\n"
            "  btc-pure broadcast-tx --network testnet --peer-index 0 --raw-file tx.hex\n"
            "  btc-pure address --secret-hex <secret_hex>\n"
            "  btc-pure tx-decode --raw-file tx.hex\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    keys_p = sub.add_parser("keys", help="generate secp256k1 secret + legacy addresses")
    keys_p.add_argument("--format", choices=("text", "json", "quiet"), default="text")
    keys_p.add_argument("--no-secret", action="store_true", help="omit printing the private key")
    keys_p.add_argument("--out", help="write JSON output to a file")
    keys_p.set_defaults(func=_cmd_keys)

    bc = sub.add_parser("broadcast-tx", help="handshake with a peer and send a tx message")
    bc.add_argument("--network", choices=("mainnet", "testnet"), default="testnet")
    bc.add_argument("--host", help="skip DNS discovery")
    bc.add_argument("--port", type=int)
    bc.add_argument("--timeout", type=float, default=20.0, help="connect + handshake timeout seconds")
    bc.add_argument("--dry-run", action="store_true", help="print what would happen without sending")
    bc.add_argument("--list-peers", action="store_true", help="print peers from DNS seeds and exit")
    bc.add_argument("--peer-index", type=int, help="use Nth DNS peer (use with --list-peers)")
    bc.add_argument("--peer-limit", type=int, default=16, help="how many peers to resolve from DNS seeds")
    bc.add_argument("--raw-stdin", action="store_true", help="read hex tx from stdin")
    g = bc.add_mutually_exclusive_group(required=False)
    g.add_argument("--raw-hex")
    g.add_argument("--raw-file", help="path containing hex serialized tx")
    bc.set_defaults(func=_cmd_broadcast)

    txid_p = sub.add_parser("txid", help="convert txid endianness (explorer <-> wire)")
    txid_p.add_argument("direction", choices=("to-wire", "from-wire"))
    txid_p.add_argument("txid_hex")
    txid_p.set_defaults(func=_cmd_txid)

    vh = sub.add_parser("validate-hex", help="validate hex and print decoded byte length")
    vh.add_argument("hex")
    vh.set_defaults(func=_cmd_validate_hex)

    doc = sub.add_parser("doctor", help="quick environment and DNS peer sanity checks")
    doc.add_argument("--network", choices=("mainnet", "testnet"), default="testnet")
    doc.add_argument("--peer-limit", type=int, default=16)
    doc.set_defaults(func=_cmd_doctor)

    addr = sub.add_parser("address", help="derive legacy P2PKH address from secret or compressed pubkey")
    g2 = addr.add_mutually_exclusive_group(required=True)
    g2.add_argument("--secret-hex", help="32-byte private key hex")
    g2.add_argument("--pubkey-hex", help="33-byte compressed pubkey hex (starts 02/03)")
    addr.add_argument("--network", choices=("mainnet", "testnet", "both"), default="both")
    addr.set_defaults(func=_cmd_address)

    td = sub.add_parser("tx-decode", help="decode a legacy raw transaction and print a summary")
    td.add_argument("--format", choices=("text", "json"), default="text")
    g3 = td.add_mutually_exclusive_group(required=True)
    g3.add_argument("--raw-hex")
    g3.add_argument("--raw-file")
    td.set_defaults(func=_cmd_tx_decode)

    args = p.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(f"error: {e}") from e


if __name__ == "__main__":
    main()
