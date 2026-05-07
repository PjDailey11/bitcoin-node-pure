"""CLI entry — wallet keys, P2P relay, Rich UI, and interactive wizards."""

from __future__ import annotations

import argparse
import asyncio
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
from bitcoin_node.config import load_merged_config
from bitcoin_node.core.tx import parse_transaction
from bitcoin_node.crypto.sha256 import sha256d
from bitcoin_node.doctor_latency import probe_peer_latency
from bitcoin_node.node import relay_raw_transaction_sync
from bitcoin_node.p2p.dns_seeds import gather_peers
from bitcoin_node.store import (
    add_utxo,
    clear_utxos,
    default_db_path,
    list_utxos,
    open_db,
    total_sats,
)
from bitcoin_node.version import __version__
from bitcoin_node.wallet import VERSION_MAINNET, VERSION_TESTNET, new_wallet_key
from bitcoin_node.crypto.base58 import b58check_encode
from bitcoin_node.crypto.ripemd160 import hash160
from bitcoin_node.crypto.secp256k1 import parse_privkey, pubkey_bytes_compressed, pubkey_from_private

try:
    import questionary
except ImportError as _e:  # pragma: no cover
    questionary = None  # type: ignore[assignment]

try:
    from bitcoin_node.cli_rich import (
        make_console,
        print_banner,
        print_hex_line,
        print_key_material,
    )
except ImportError:
    make_console = print_banner = print_hex_line = print_key_material = None  # type: ignore[misc, assignment]


def _run_async_gather_peers(network: str, limit: int) -> list[tuple[str, int]]:
    return asyncio.run(gather_peers(network, limit=limit))


def _get_console(no_color: bool) -> object | None:
    if make_console:
        return make_console(no_color=no_color)
    return None


def _cmd_keys(args: argparse.Namespace) -> None:
    w = new_wallet_key()
    hide = args.hide_secret or args.no_secret
    payload = {
        "secret_hex": None if hide else w.secret_bytes.hex(),
        "pubkey_compressed_hex": w.pubkey_compressed.hex(),
        "address_mainnet": w.address_mainnet,
        "address_testnet": w.address_testnet,
    }

    if (
        not hide
        and args.format != "quiet"
        and sys.stdout.isatty()
        and not getattr(args, "yes", False)
    ):
        if questionary:
            ok = questionary.confirm(
                "[SECURITY] Show private key (secret_hex) on screen? Never share it.",
                default=False,
            ).ask()
            if ok is not True:
                hide = True
                payload["secret_hex"] = None

    if args.format == "json" or args.out:
        rendered = json.dumps(payload, indent=2, sort_keys=True)
        if args.out:
            Path(args.out).write_text(rendered + "\n", encoding="utf-8")
            if args.format != "quiet":
                c = _get_console(args.no_color)
                if c:
                    c.print(f"[green]wrote:[/] {args.out}")
                else:
                    print(f"wrote: {args.out}")
            return
        if args.format == "json":
            c = _get_console(args.no_color)
            if c and print_key_material:
                from rich.syntax import Syntax

                c.print(Syntax(rendered, "json", theme="monokai", word_wrap=True))
            else:
                print(rendered)
        return
    if args.format == "quiet":
        return

    c = _get_console(args.no_color)
    if c and print_key_material:
        if not args.no_banner:
            print_banner(c)
        print_key_material(
            c,
            secret_hex=payload["secret_hex"],
            pubkey_hex=payload["pubkey_compressed_hex"],
            main_a=payload["address_mainnet"],
            test_a=payload["address_testnet"],
            format_json=False,
            payload_obj=payload,
        )
    else:
        if payload["secret_hex"] is not None:
            print("secret_hex:", payload["secret_hex"])
        print("pubkey_compressed_hex:", payload["pubkey_compressed_hex"])
        print("address_mainnet:", payload["address_mainnet"])
        print("address_testnet:", payload["address_testnet"])


def _cmd_broadcast(args: argparse.Namespace) -> None:
    if args.list_peers:
        peers = _run_async_gather_peers(args.network, args.peer_limit)
        c = _get_console(args.no_color)
        for i, (h, p) in enumerate(peers):
            line = f"[{i}] {h}:{p}"
            if c:
                c.print(line)
            else:
                print(line)
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

    def wire_dbg(label: str, blob: bytes) -> None:
        c = _get_console(args.no_color)
        if c and print_hex_line:
            print_hex_line(c, label, blob)
        else:
            print(f"{label} ({len(blob)} bytes): {blob.hex()}")

    if args.dry_run:
        c = _get_console(args.no_color)
        msg = f"dry-run: would connect to {host or '<dns-seed>'} on {args.network} and send {len(raw)} bytes"
        if c:
            c.print(f"[yellow]{msg}[/]")
            c.print("[dim]tip: btc-pure broadcast-tx --list-peers[/]")
        else:
            print(msg)
        return

    relay_raw_transaction_sync(
        args.network,
        raw,
        host=host,
        port=port,
        timeout=args.timeout,
        dry_run=False,
        wire_debug=wire_dbg if (args.verbose or args.debug) else None,
    )
    c = _get_console(args.no_color)
    m = f"sent {len(raw)} byte serialized transaction (best-effort)"
    if c:
        c.print(f"[green]{m}[/]")
    else:
        print(m)


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
    c = _get_console(args.no_color)
    if c:
        c.print(f"[green]ok: {len(b)} bytes[/]")
    else:
        print(f"ok: {len(b)} bytes")


async def _doctor_latency_probe(
    network: str, peers: list[tuple[str, int]], limit: int, *, no_color: bool
) -> None:
    for i, (host, prt) in enumerate(peers[:limit]):
        tcp_ms, rtt_ms, status = await probe_peer_latency(host, prt, network=network)
        line = f"[{i}] {host}:{prt}"
        if tcp_ms is not None:
            line += f" | tcp {tcp_ms:7.1f} ms"
        if rtt_ms is not None:
            line += f" | version_rtt {rtt_ms:7.1f} ms"
        line += f" | {status}"
        c = _get_console(no_color)
        if c:
            c.print(line)
        else:
            print(line)


def _cmd_doctor(args: argparse.Namespace) -> None:
    c = _get_console(args.no_color)
    if c:
        print_banner(c)
    peers = _run_async_gather_peers(args.network, args.peer_limit)
    if not peers:
        raise SystemExit("dns: no peers returned (try --network testnet or pass --host/--port)")

    msg = (
        f"bitcoin-node-pure doctor | v{__version__} | "
        f"Python {sys.version.split()[0]} ({platform.platform()}) | network={args.network}"
    )
    if c:
        c.print(msg)
        c.print(f"[bold]dns:[/] resolved {len(peers)} peers")
    else:
        print(msg)
        print("dns: resolved", len(peers), "peers")

    if not getattr(args, "no_latency", False):
        asyncio.run(
            _doctor_latency_probe(args.network, peers, args.latency_limit, no_color=args.no_color)
        )
    else:
        for i, (h, p) in enumerate(peers[:5]):
            if c:
                c.print(f"[{i}] {h}:{p}")
            else:
                print(f"[{i}] {h}:{p}")
    if c:
        c.print("[bold green]ok[/]")
    else:
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
        c = _get_console(args.no_color)
        if c:
            from rich.syntax import Syntax

            c.print(Syntax(json.dumps(summary, indent=2), "json", theme="monokai"))
        else:
            for k, v in summary.items():
                print(f"{k}: {v}")


def _cmd_tx_encode(args: argparse.Namespace) -> None:
    from bitcoin_node.tx_wizard import run_tx_encode_wizard

    run_tx_encode_wizard(no_color=args.no_color)


def _cmd_cache(args: argparse.Namespace) -> None:
    dbp = Path(args.db) if args.db else default_db_path()
    con = open_db(dbp)
    if args.cache_cmd == "list":
        rows = list_utxos(con, args.network if args.network else None)
        for r in rows:
            print(*r, sep="\t")
    elif args.cache_cmd == "balance":
        tot = total_sats(con, args.network if args.network else None)
        print("total_sats:", tot)
    elif args.cache_cmd == "clear":
        n = clear_utxos(con, args.network if args.network else None)
        print("deleted rows:", n)
    elif args.cache_cmd == "add":
        add_utxo(
            con,
            network=args.network or "testnet",
            txid_be_hex=args.txid.replace(" ", ""),
            vout=args.vout,
            value_sats=args.value,
            script_pubkey_hex=args.script_hex.replace(" ", ""),
        )
        print("stored", args.txid, args.vout)


def _run_interactive_menu(cfg, no_color: bool) -> None:
    if not questionary:
        raise SystemExit("Install questionary: pip install questionary")
    choice = questionary.select(
        "btc-pure — choose an action",
        choices=[
            "keys — generate wallet",
            "doctor — network check",
            "tx-encode — build/sign tx (wizard)",
            "broadcast-tx — send raw hex",
            "exit",
        ],
    ).ask()
    if choice is None or choice.startswith("exit"):
        return
    if choice.startswith("keys"):
        ns = argparse.Namespace(
            format="text",
            no_secret=False,
            hide_secret=False,
            yes=False,
            out=None,
            no_color=no_color,
            no_banner=False,
        )
        _cmd_keys(ns)
    elif choice.startswith("doctor"):
        ns = argparse.Namespace(
            network=cfg.network,
            peer_limit=cfg.peer_limit,
            no_latency=False,
            latency_limit=5,
            no_color=no_color,
        )
        _cmd_doctor(ns)
    elif choice.startswith("tx-encode"):
        _cmd_tx_encode(argparse.Namespace(no_color=no_color))
    elif choice.startswith("broadcast"):
        hx = questionary.text("Path to hex file or paste hex (or empty to cancel):").ask()
        if not hx:
            return
        p = Path(hx)
        raw_hex = p.read_text(encoding="utf-8") if p.is_file() else hx
        ns = argparse.Namespace(
            network=cfg.network,
            host=None,
            port=None,
            timeout=20.0,
            dry_run=False,
            list_peers=False,
            peer_index=0,
            peer_limit=cfg.peer_limit,
            raw_stdin=False,
            raw_hex=raw_hex if not p.is_file() else None,
            raw_file=str(p) if p.is_file() else None,
            verbose=False,
            debug=False,
            no_color=no_color,
        )
        if p.is_file():
            ns.raw_hex = None
            ns.raw_file = str(p)
        else:
            ns.raw_hex = raw_hex.strip()
            ns.raw_file = None
        _cmd_broadcast(ns)


def build_parser(cfg_path: Path | None, cfg) -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--config", type=Path, default=cfg_path, help="path to .btc-pure.yaml")
    parent.add_argument("--no-color", action="store_true", help="disable Rich colors")

    p = argparse.ArgumentParser(
        prog="btc-pure",
        parents=[parent],
        description="bitcoin-node-pure — cryptographic + P2P lab toolkit",
        epilog=(
            "Environment: BTC_NETWORK or BTC_PURE_NETWORK = mainnet|testnet\n"
            "Config file: .btc-pure.yaml (cwd or home) — keys: network, peer_limit\n\n"
            "Examples:\n"
            "  btc-pure keys\n"
            "  btc-pure doctor --network testnet\n"
            "  btc-pure tx-encode\n"
            "  btc-pure broadcast-tx --verbose --network testnet --raw-file tx.hex\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=False)

    keys_p = sub.add_parser("keys", help="generate secp256k1 secret + legacy addresses")
    keys_p.add_argument("--format", choices=("text", "json", "quiet"), default="text")
    keys_p.add_argument("--no-secret", action="store_true", help="omit printing the private key")
    keys_p.add_argument("--hide-secret", action="store_true", help="alias of --no-secret")
    keys_p.add_argument("--yes", "-y", action="store_true", help="skip confirmation before printing secret")
    keys_p.add_argument("--out", help="write JSON output to a file")
    keys_p.add_argument("--no-banner", action="store_true", help="skip ASCII banner")
    keys_p.set_defaults(func=_cmd_keys)

    bc = sub.add_parser("broadcast-tx", help="handshake with a peer and send a tx message")
    bc.add_argument("--network", choices=("mainnet", "testnet"), default=cfg.network)
    bc.add_argument("--host", help="skip DNS discovery")
    bc.add_argument("--port", type=int)
    bc.add_argument("--timeout", type=float, default=20.0, help="connect + handshake timeout seconds")
    bc.add_argument("--dry-run", action="store_true", help="print what would happen without sending")
    bc.add_argument("--list-peers", action="store_true", help="print peers from DNS seeds and exit")
    bc.add_argument("--peer-index", type=int, help="use Nth DNS peer")
    bc.add_argument("--peer-limit", type=int, default=cfg.peer_limit, help="peers to resolve from DNS seeds")
    bc.add_argument("--raw-stdin", action="store_true", help="read hex tx from stdin")
    bc.add_argument("--verbose", action="store_true", help="log full wire frames (hex)")
    bc.add_argument("--debug", action="store_true", help="alias of --verbose")
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

    doc = sub.add_parser("doctor", help="environment + DNS + optional TCP latency")
    doc.add_argument("--network", choices=("mainnet", "testnet"), default=cfg.network)
    doc.add_argument("--peer-limit", type=int, default=cfg.peer_limit)
    doc.add_argument("--latency-limit", type=int, default=5, help="how many peers to probe")
    doc.add_argument(
        "--no-latency",
        action="store_true",
        help="only list DNS peers (skip TCP + RTT probes)",
    )
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

    te = sub.add_parser("tx-encode", help="interactive wizard to build & sign a legacy P2PKH transaction")
    te.set_defaults(func=_cmd_tx_encode)

    wz = sub.add_parser("wizard", help="interactive menu (same as running btc-pure with no subcommand)")
    wz.set_defaults(func=None)

    cache = sub.add_parser("cache", help="local SQLite UTXO metadata cache")
    cs = cache.add_subparsers(dest="cache_cmd", required=True)
    c_list = cs.add_parser("list", help="list cached entries")
    c_list.add_argument("--network", choices=("mainnet", "testnet"), default=None)
    c_list.add_argument("--db", type=str, default=None, help="sqlite path (default ~/.btc-pure/cache.sqlite3)")
    c_list.set_defaults(func=_cmd_cache)

    c_bal = cs.add_parser("balance", help="sum cached values (sats)")
    c_bal.add_argument("--network", choices=("mainnet", "testnet"), default=None)
    c_bal.add_argument("--db", type=str, default=None)
    c_bal.set_defaults(func=_cmd_cache)

    c_cl = cs.add_parser("clear", help="delete cached rows")
    c_cl.add_argument("--network", choices=("mainnet", "testnet"), default=None)
    c_cl.add_argument("--db", type=str, default=None)
    c_cl.set_defaults(func=_cmd_cache)

    c_ad = cs.add_parser("add", help="add a UTXO record manually")
    c_ad.add_argument("--network", choices=("mainnet", "testnet"), required=True)
    c_ad.add_argument("--txid", required=True, help="explorer-style txid (big-endian hex)")
    c_ad.add_argument("--vout", type=int, required=True)
    c_ad.add_argument("--value", type=int, required=True, help="value in satoshis")
    c_ad.add_argument("--script-hex", required=True, dest="script_hex")
    c_ad.add_argument("--db", type=str, default=None)
    c_ad.set_defaults(func=_cmd_cache)

    return p


def main() -> None:
    pre_cfg = argparse.ArgumentParser(add_help=False)
    pre_cfg.add_argument("--config", type=Path, default=None)
    pre_args, _ = pre_cfg.parse_known_args()

    cfg = load_merged_config(pre_args.config)

    if len(sys.argv) == 1:
        c = _get_console(False)
        if c and print_banner:
            print_banner(c)
        _run_interactive_menu(cfg, no_color=False)
        return

    parser = build_parser(pre_args.config, cfg)
    args = parser.parse_args()

    if getattr(args, "hide_secret", False):
        args.no_secret = True

    if args.cmd is None or args.cmd == "wizard":
        _run_interactive_menu(cfg, no_color=args.no_color)
        return

    try:
        if args.func is None:
            _run_interactive_menu(cfg, no_color=args.no_color)
            return
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(f"error: {e}") from e


if __name__ == "__main__":
    main()
