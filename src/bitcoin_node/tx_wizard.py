"""Interactive legacy P2PKH transaction builder (wizard)."""

from __future__ import annotations

from pathlib import Path

import questionary

from bitcoin_node.cli_helpers import decode_hex, txid_to_wire_le
from bitcoin_node.core.script import p2pkh_script_pubkey
from bitcoin_node.core.tx import Transaction, TxIn, TxOut, sign_p2pkh_input
from bitcoin_node.crypto.base58 import b58check_decode
from bitcoin_node.crypto.ripemd160 import hash160
from bitcoin_node.crypto.secp256k1 import parse_privkey, pubkey_bytes_compressed, pubkey_from_private
from bitcoin_node.wallet import VERSION_MAINNET, VERSION_TESTNET

try:
    from bitcoin_node.cli_rich import make_console
except Exception:
    make_console = None  # type: ignore[misc, assignment]


def _parse_priv(secret_hex: str) -> bytes:
    b = decode_hex(secret_hex)
    parse_privkey(b)
    return b


def run_tx_encode_wizard(*, no_color: bool = False) -> None:
    console = make_console(no_color=no_color) if make_console else None

    q = questionary.text(
        "Private key (64 hex chars) or leave empty to generate a new random key:",
        default="",
    ).ask()
    if q is None:
        raise SystemExit("cancelled")
    q = (q or "").strip()
    if not q:
        from bitcoin_node.wallet import new_wallet_key

        w = new_wallet_key()
        priv = w.secret_bytes
        if console:
            console.print("[yellow]generated new wallet key (save secret_hex safely)[/]")
            console.print("[red bold]secret_hex:[/]", priv.hex())
        else:
            print("secret_hex:", priv.hex())
    else:
        priv = _parse_priv(q)

    pub = pubkey_from_private(parse_privkey(priv))
    pkc = pubkey_bytes_compressed(pub)
    my_spk = p2pkh_script_pubkey(hash160(pkc))

    def _valid_txid(t: str) -> bool | str:
        s = "".join(t.split())
        if len(s) != 64:
            return "must be 64 hex characters"
        try:
            decode_hex(s)
        except ValueError:
            return "invalid hex"
        return True

    prev_explorer = questionary.text(
        "Previous txid (64 hex, explorer / big-endian style):",
        validate=_valid_txid,
    ).ask()
    if not prev_explorer:
        raise SystemExit("cancelled")
    prev_wire = decode_hex(txid_to_wire_le(prev_explorer.replace(" ", "")))

    vout_s = questionary.text("Previous output index (vout):", default="0").ask()
    vout = int(vout_s or "0")

    val_in_s = questionary.text("Input value (satoshis in that UTXO):", default="100000").ask()
    val_in = int(val_in_s or "0")

    fee_s = questionary.text("Fee (satoshis):", default="1000").ask()
    fee = int(fee_s or "0")

    dest = questionary.select(
        "Send to:",
        choices=["Same address as this key (self-transfer demo)", "Custom Base58 address"],
    ).ask()
    if dest is None:
        raise SystemExit("cancelled")

    if dest.startswith("Same"):
        dest_spk = my_spk
    else:
        addr = questionary.text("Destination legacy P2PKH address (starts with 1, m, or n):").ask()
        if not addr:
            raise SystemExit("cancelled")
        ver, payload = b58check_decode(addr)
        if ver not in (VERSION_MAINNET, VERSION_TESTNET) or len(payload) != 20:
            raise SystemExit("unsupported address (expect mainnet/testnet P2PKH)")
        dest_spk = p2pkh_script_pubkey(payload)

    out_val = val_in - fee
    if out_val <= 0:
        raise SystemExit("outputs must be positive — lower fee or raise input value")

    tx = Transaction(1, (TxIn(prev_wire, vout, b"", 0xFFFFFFFF),), (TxOut(out_val, dest_spk),), 0)

    signed = sign_p2pkh_input(tx, 0, priv, my_spk)
    raw_hex = signed.serialize().hex()

    if console:
        console.print("\n[bold green]Signed transaction (hex):[/]")
        console.print(raw_hex)
    else:
        print(raw_hex)

    save = questionary.confirm("Save raw hex to a file?", default=False).ask()
    if save:
        path = questionary.text("File path:", default="signed_tx.hex").ask()
        if path:
            Path(path).write_text(raw_hex + "\n", encoding="utf-8")
            print("wrote:", path)


if __name__ == "__main__":
    run_tx_encode_wizard()
