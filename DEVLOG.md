# DEVLOG — bitcoin-node-pure

Maintainers append dated sections after **major** milestones (features, breaking fixes, protocol-facing adjustments).

---

## 2026-05-07 — Rich CLI, config, latency probes, SQLite cache

### What changed

- Added runtime dependencies: **rich**, **PyYAML**, **questionary** (core crypto modules unchanged).
- **Rich**-styled output for keys/JSON; ASCII-only banner + `box.ASCII` for Windows consoles.
- **Keys security:** `--hide-secret` / `--no-secret`, interactive confirm on TTY unless `-y`.
- **`doctor`:** TCP connect ms + first `version` round-trip ms (`--no-latency` skips probes).
- **`broadcast-tx --verbose`:** dumps full P2P frame hex via `wire_debug` on `BitcoinPeer`.
- **`tx-encode`:** interactive legacy P2PKH builder (`tx_wizard.py`).
- **Config:** `.btc-pure.yaml` + `BTC_*NETWORK` env; `load_merged_config`.
- **`cache`:** SQLite UTXO metadata (`~/.btc-pure/cache.sqlite3`).
- **`btc-pure` / `wizard`:** menu when run with no subcommand.
- Example: `examples/btc-pure.example.yaml`.

### Next steps

- Optional sync from bitcoind/ZMQ for real UTXO set (large scope).

---

## 2026-05-06 — Initial repository scaffold

### What changed

- Created `bitcoin-node-pure` under `bitcoin-node-python/` with `pyproject.toml`, editable install, and console script `btc-pure`.
- Implemented **SHA-256** (fixed `CH` ~ masking + official `K[]` constants), **RIPEMD-160** (Rosetta/word-wise formulation validated vs `hashlib`), **HASH160**, **Base58Check**, **DER**, and **secp256k1 affine math** + **RFC6979 deterministic ECDSA** + **low-S** normalization.
- Delivered **legacy transaction** serialization/deserialization, **SIGHASH_ALL** signing path, immutable **UTXO snapshots** with explicit fee accounting helpers.
- Added asyncio **P2P peer** with DNS seed resolution (stdlib `getaddrinfo`), **version/verack** handshake, optional **ping/pong**, and **`tx` relay** hook.
- Tests cover hashes, ECC sanity checks, tx smoke flow, and UTXO fee math; CLI exposes `keys` + `broadcast-tx`.
- Authored Raspberry Pi deployment outline + bootstrap shell stub (`scripts/pi_bootstrap.sh`) and Lightning appendix targeting **LND + Alby Hub**.

### Why

The goal is a **zero third-party dependency** narrative useful for teaching deterministic systems engineering without implying production-ready consensus participation.

### Known gaps / intentional limits

- No mempool policy engine, no compact blocks, no witness serialization, no consensus-critical CVE regressions matrix.
- DNS discovery filters IPv4 only; IPv6-only peers are skipped.
- Modern Bitcoin Core may ignore unsolicited `tx` frames — inv/getdata flow is illustrated elsewhere in code (`send_inv_tx`) but not wired into CLI defaults.

### Next steps

- Optional JSON-RPC bridge solely for local labs (still stdlib) gated behind explicit flags.
- Witness/V0 P2WPKH module mirroring BIP143 preimage construction.
- Extend handshake state machine with explicit ping negotiation timeouts + peer scoring hooks for classroom demos.
