"""SQLite cache for locally recorded UTXO metadata (lab / wallet helper)."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def default_db_path() -> Path:
    return Path.home() / ".btc-pure" / "cache.sqlite3"


def open_db(path: Path | None = None) -> sqlite3.Connection:
    p = path or default_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS utxos (
            outpoint_hex TEXT PRIMARY KEY,
            network TEXT NOT NULL,
            txid_be TEXT NOT NULL,
            vout INTEGER NOT NULL,
            value_sats INTEGER NOT NULL,
            script_pubkey_hex TEXT NOT NULL
        )
        """
    )
    con.commit()
    return con


def add_utxo(
    con: sqlite3.Connection,
    *,
    network: str,
    txid_be_hex: str,
    vout: int,
    value_sats: int,
    script_pubkey_hex: str,
) -> None:
    op = f"{txid_be_hex}:{vout}"
    con.execute(
        """
        INSERT OR REPLACE INTO utxos (outpoint_hex, network, txid_be, vout, value_sats, script_pubkey_hex)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (op, network, txid_be_hex, vout, value_sats, script_pubkey_hex.lower()),
    )
    con.commit()


def list_utxos(con: sqlite3.Connection, network: str | None = None) -> list[tuple[str, str, int, int, str]]:
    if network:
        cur = con.execute(
            "SELECT network, txid_be, vout, value_sats, script_pubkey_hex FROM utxos WHERE network = ?",
            (network,),
        )
    else:
        cur = con.execute("SELECT network, txid_be, vout, value_sats, script_pubkey_hex FROM utxos")
    return list(cur.fetchall())


def clear_utxos(con: sqlite3.Connection, network: str | None = None) -> int:
    if network:
        cur = con.execute("DELETE FROM utxos WHERE network = ?", (network,))
    else:
        cur = con.execute("DELETE FROM utxos")
    con.commit()
    return cur.rowcount or 0


def total_sats(con: sqlite3.Connection, network: str | None = None) -> int:
    if network:
        cur = con.execute("SELECT COALESCE(SUM(value_sats),0) FROM utxos WHERE network = ?", (network,))
    else:
        cur = con.execute("SELECT COALESCE(SUM(value_sats),0) FROM utxos")
    return int(cur.fetchone()[0])
