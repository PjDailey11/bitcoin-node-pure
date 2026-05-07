# bitcoin-node-pure

Zero third-party dependencies (stdlib only): secp256k1-style ECDSA, SHA-256, RIPEMD-160, legacy P2PKH, transaction serialization, immutable UTXO-style ledger modeling, and a minimal asyncio Bitcoin P2P client for handshakes and `tx` relay.

**Scope.** This is an engineering demonstration and learning codebase. It does **not** implement a competitive full-chain syncing node; validating every consensus rule or staying aligned with all soft forks is out of scope.

## Layout

| Conceptual area | Package path |
|-----------------|--------------|
| ECC + hashes + Base58 | `src/bitcoin_node/crypto/` |
| UTXO model + transactions | `src/bitcoin_node/core/` |
| P2P framing + messages | `src/bitcoin_node/p2p/` |

Entry modules: `bitcoin_node.wallet`, `bitcoin_node.node`, `bitcoin_node.cli`.

## Install / run

```bash
cd bitcoin-node-python
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
btc-pure --help
```

Or without install:

```bash
set PYTHONPATH=src
python -m bitcoin_node.cli --help
```

## Quickstart (what you can do today)

- Generate a valid secp256k1 secret key, compressed pubkey, and legacy P2PKH addresses:

```bash
btc-pure keys
```

- Run the full test suite:

```bash
pytest -q
```

## CLI commands

```bash
btc-pure keys
btc-pure broadcast-tx --network testnet --raw-file tx.hex
```

### Broadcasting a raw transaction

Write a hex-encoded legacy (non-segwit) transaction to a file (e.g. `tx.hex`) and run:

```bash
btc-pure broadcast-tx --network testnet --raw-file tx.hex
```

Note: many modern peers ignore unsolicited `tx` messages. This code sends `tx` directly as a best-effort demo of message framing and handshakes.

### Constructing + signing a legacy P2PKH transaction (library usage)

The project includes legacy serialization and SIGHASH_ALL signing for P2PKH spends. A minimal flow is:

```python
from bitcoin_node.core.script import p2pkh_script_pubkey
from bitcoin_node.core.tx import Transaction, TxIn, TxOut, sign_p2pkh_input
from bitcoin_node.crypto.ripemd160 import hash160
from bitcoin_node.crypto.secp256k1 import parse_privkey, pubkey_bytes_compressed, pubkey_from_private

privkey = bytes.fromhex("<32-byte-secret-hex>")
pub = pubkey_from_private(parse_privkey(privkey))
spk = p2pkh_script_pubkey(hash160(pubkey_bytes_compressed(pub)))

prev_txid_le = bytes.fromhex("<32-byte-prev-txid-le-hex>")
tx = Transaction(
    1,
    (TxIn(prev_txid_le, 0, b"", 0xFFFFFFFF),),
    (TxOut(100_000 - 1_000, spk),),  # value minus fee
    0,
)
signed = sign_p2pkh_input(tx, 0, privkey, spk)
raw_hex = signed.serialize().hex()
```

## Raspberry Pi deployment + Lightning context

See [`docs/RASPBERRY_PI_DEPLOYMENT.md`](docs/RASPBERRY_PI_DEPLOYMENT.md) for Raspberry Pi 5 + SSD guidance and optional **LND + Alby Hub** reading notes.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

(`dev` extra only adds `pytest`—still no runtime deps.)

## DEVLOG

See root [`DEVLOG.md`](DEVLOG.md) for milestone entries (what / why / next steps).

## Physical deployment + Lightning context

[`docs/RASPBERRY_PI_DEPLOYMENT.md`](docs/RASPBERRY_PI_DEPLOYMENT.md) covers Raspberry Pi 5 + SSD guidance and optional **LND + Alby Hub** reading notes.
