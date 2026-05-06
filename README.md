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
pip install -e .
python -m bitcoin_node.cli --help
```

Or without install:

```bash
set PYTHONPATH=src
python -m bitcoin_node.cli --help
```

## CLI examples

```bash
btc-pure keys
btc-pure address --network testnet
btc-pure broadcast-tx --network testnet --raw-file tx.hex
```

See `docs/RASPBERRY_PI_DEPLOYMENT.md` for hardware deployment notes and optional Lightning stack pointers.

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
