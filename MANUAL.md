# Manual — bitcoin-node-pure

This is a **learning** codebase that re-implements core Bitcoin building blocks with **zero runtime dependencies** (stdlib only). It is not a production full node and it does not attempt full consensus validation or full-chain sync.

## What’s included

- **Cryptography (pure Python)**:
  - SHA-256 (`sha256`, `sha256d`)
  - RIPEMD-160 + `HASH160`
  - Base58Check (legacy address format)
  - secp256k1 affine point arithmetic + ECDSA (RFC6979 deterministic nonce + low-S)
  - DER signature encoding/decoding (Bitcoin scriptSig format)
- **Legacy transactions**:
  - varints, endianness, serialization + parsing
  - minimal scripts for legacy P2PKH
  - legacy `SIGHASH_ALL` signing flow
- **UTXO snapshots**:
  - immutable snapshot updates
  - implicit fee computation \(inputs − outputs\)
- **P2P demo**:
  - DNS seeding, TCP connect, `version/verack` handshake
  - best-effort `tx` relay

## Install (Windows / PowerShell)

```powershell
cd C:\Users\User\.claude\workspaces\bitcoin-node-python
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
```

Run tests:

```powershell
pytest -q
```

## CLI usage

Show help:

```powershell
btc-pure --help
```

### 1) Generate keys + addresses

```powershell
btc-pure keys
```

You’ll get:

- `secret_hex`: 32-byte private key
- `pubkey_compressed_hex`: 33-byte compressed public key
- `address_mainnet`: legacy P2PKH address (prefix `1…`)
- `address_testnet`: legacy P2PKH address (prefix `m…` or `n…`)

**Safety**: do not use these keys for real funds.

### 2) Broadcast a raw transaction (best-effort demo)

This uses DNS seeds by default, handshakes, and then sends a `tx` message.

```powershell
btc-pure broadcast-tx --network testnet --raw-file tx.hex
```

Or inline:

```powershell
btc-pure broadcast-tx --network testnet --raw-hex "<hex>"
```

Optional:

```powershell
btc-pure broadcast-tx --network testnet --host 1.2.3.4 --port 18333 --raw-file tx.hex
```

### Why “best-effort”?

Many modern nodes ignore unsolicited `tx` messages unless you follow a more complete relay flow (e.g. `inv` → `getdata` → `tx`) and satisfy policy checks. This repo’s P2P layer is primarily a **framing + handshake** demonstration.

## Library usage walkthrough (construct + sign a legacy P2PKH tx)

This is the minimal happy-path for building a *legacy* tx that spends a single P2PKH UTXO and creates one P2PKH output.

Prerequisites (you must know the UTXO you’re spending):

- `prev_txid` (32 bytes) — **wire-order little-endian** bytes
- `prev_index` (vout)
- previous output’s **`scriptPubKey`** (the P2PKH locking script you’re spending)
- previous output’s **value** (for fee math; signing doesn’t require it, but wallets do)

Example:

```python
from bitcoin_node.core.script import p2pkh_script_pubkey
from bitcoin_node.core.tx import Transaction, TxIn, TxOut, sign_p2pkh_input
from bitcoin_node.crypto.ripemd160 import hash160
from bitcoin_node.crypto.secp256k1 import parse_privkey, pubkey_bytes_compressed, pubkey_from_private

# 1) Your keypair
privkey = bytes.fromhex("<32-byte-secret-hex>")
pub = pubkey_from_private(parse_privkey(privkey))

# 2) Destination output script (pay to your own pubkey hash here)
dest_spk = p2pkh_script_pubkey(hash160(pubkey_bytes_compressed(pub)))

# 3) The UTXO you are spending (prev txid in *little-endian* wire order)
prev_txid_le = bytes.fromhex("<32-byte-prev-txid-le-hex>")
prev_vout = 0
prev_script_pubkey = dest_spk  # for a self-spend demo; real wallets use the actual prev script

# 4) Build an unsigned tx (scriptSig empty)
value_in = 100_000         # satoshis in the UTXO (example)
fee = 1_000                # satoshis (example)
value_out = value_in - fee

tx = Transaction(
    1,
    (TxIn(prev_txid_le, prev_vout, b"", 0xFFFFFFFF),),
    (TxOut(value_out, dest_spk),),
    0,
)

# 5) Sign input 0 (legacy SIGHASH_ALL)
signed = sign_p2pkh_input(tx, 0, privkey, prev_script_pubkey)
raw_hex = signed.serialize().hex()
print(raw_hex)
```

### Notes on endianness

- Transaction hashes are typically shown by explorers as big-endian hex.
- Bitcoin’s legacy wire encoding stores tx hashes as **little-endian** in `TxIn.prev_txid`.
- If you copy a txid from an explorer, you usually must **reverse the bytes** to produce the wire-order `prev_txid` field.

## Common troubleshooting

- **“Cannot find path … bitcoin-node-python”**: the repo is in `C:\Users\User\.claude\workspaces\bitcoin-node-python`, not your home directory.
- **`pip install -e` fails**: make sure your venv is activated and you’re in the repo root where `pyproject.toml` exists.
- **Broadcast appears to do nothing**: peers can ignore your `tx` message; ensure you’re on `testnet` and that the tx is valid and policy-acceptable.

## Next expansions (optional)

- Implement witness serialization (P2WPKH) and BIP143 sighash preimages.
- Add a minimal `inv/getdata/tx` relay loop in the P2P layer.
- Add a local JSON-RPC adapter for lab-only workflows (still stdlib).

