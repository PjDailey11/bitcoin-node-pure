#!/usr/bin/env bash
# Debian/Ubuntu/Raspberry Pi OS bootstrap — installs Python tooling on minimal SSD-backed Pi setups.
set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  echo "run as normal user with sudo when prompted"
  exit 1
fi

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git rsync

PROJECT_SRC="${1:?clone bitcoin-node-python to ~/bitcoin-node-python and pass path}"
cd "${PROJECT_SRC}"
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
pytest -q

echo "bootstrap finished — activate with: source ${PROJECT_SRC}/.venv/bin/activate"
