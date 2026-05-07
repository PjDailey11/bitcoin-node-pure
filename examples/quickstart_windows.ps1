$ErrorActionPreference = "Stop"

Write-Host "bitcoin-node-pure quickstart (Windows)"
Write-Host "Repo:" (Get-Location)

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

.\.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
pytest -q

Write-Host ""
Write-Host "Try:"
Write-Host "  btc-pure keys"
Write-Host "  btc-pure doctor --network testnet"
Write-Host "  btc-pure broadcast-tx --network testnet --list-peers"

