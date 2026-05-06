# Raspberry Pi 5 headless deployment (SSD + minimal OS)

This guide complements `bitcoin-node-pure`: **do not** expect Pi-grade Python performance for consensus-critical workloads. Use this layout for **hands-on labs**, **wallet tooling**, or **protocol demos**.

## Hardware checklist

- Raspberry Pi 5 (8 GB RAM recommended if you compile kernels or auxiliary daemons).
- Official USB‑C PSU sized for SSD power budget + Pi spikes.
- **External SSD** (USB 3 enclosure or NVMe hat) as root filesystem — avoid wearing SD cards under sustained logging.
- Ethernet for stable peering during experiments.

## OS choices

| OS profile | Notes |
|------------|-------|
| Raspberry Pi OS Lite (64-bit) | Minimal Debian base; SSH enabled via `raspi-config`, predictable apt tooling. |
| Ubuntu Server for Raspberry Pi | Familiar cloud workflows; netplan + systemd cadence similar to VPS hosts. |
| **Start9-style sovereign stacks** | Projects such as StartOS bundle orchestration + web dashboards for self-hosted services. They are excellent references for **USB boot**, **LUKS**, and **update channels**, but Bitcoin Core remains the production-grade chain client — treat `bitcoin-node-pure` as a companion teaching codebase, not a drop-in replacement. |

Pick one minimal image, flash with Raspberry Pi Imager, enable SSH + pubkey auth, expand filesystem onto SSD.

## Storage layout

1. Image OS to SSD (preferred) or bootstrap SD → `raspi-config` → USB boot once firmware sees disk.
2. Mount external volumes under `/srv` for logs and wallets if you separate `/home`.
3. Consider `noatime` on SSD mount options for endurance.

## Python runtime on-device

```bash
sudo apt-get update && sudo apt-get install -y python3 python3-venv git
git clone <your-fork-or-mirror>/bitcoin-node-python.git
cd bitcoin-node-python
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

See also `scripts/pi_bootstrap.sh`.

## Headless operations

- **SSH**: `ssh pi@<device>.local` after flashing with authorized keys.
- **Reverse SSH / Tailscale / WireGuard**: expose dashboards safely — never punch arbitrary RPC ports to the public Internet without firewall rules.
- **systemd unit sketch**: wrap `python -m bitcoin_node.cli broadcast-tx ...` or REPL experiments inside `Type=simple` units with hardened `ProtectHome=`/`NoNewPrivileges=yes`.

## Lightning Network appendix (optional comprehension track)

Lightning moves payments **off-chain** via hashed timelock contracts and mutual multisigs anchored on-chain.

| Piece | Role |
|-------|------|
| **LND** | Lightning Labs daemon — channel graph sync, HTLC routing, macaroon auth. |
| **Alby Hub** | Custodial/light-hub tooling for wallets — illustrates UX bridging browsers ↔ Lightning without operating raw nodes daily. |

Integration narrative:

1. Run Bitcoin Core (or another full archival node) as your **L1 truth engine**.
2. Point `lnd`'s `bitcoind.*` RPC settings at that node; wait for sync + `btcd`/`neutrino` alternatives exist but defer to LND docs.
3. Fund channels from on-chain UTXOs produced by standard wallets (not this educational miner).
4. Use **Alby Hub** on laptops/browsers to showcase invoices + macaroons while Pi stays online routing experiment traffic.

This demonstrates why the primitives in `bitcoin-node-pure` (signatures, tx serialization, P2P framing) matter even though Lightning validators rarely rewrite ECDSA by hand.

## Safety reminders

- Never paste production mainnet keys into lab repos.
- Rate-limit P2P experiments — misconfigured nodes can get banned by honest peers.
- Keep SSD backups of wallet seeds offline (steel/paper), not on the hot Pi alone.
