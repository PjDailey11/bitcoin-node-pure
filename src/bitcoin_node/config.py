"""Load ~/.btc-pure.yaml, ./.btc-pure.yaml, and env overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


@dataclass
class AppConfig:
    network: str = "testnet"
    peer_limit: int = 16


def _safe_load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file() or yaml is None:
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def config_file_candidates(explicit: Path | None = None) -> list[Path]:
    if explicit is not None:
        return [explicit]
    home = Path.home()
    return [
        Path.cwd() / ".btc-pure.yaml",
        home / ".btc-pure.yaml",
    ]


def load_merged_config(config_path: Path | None = None) -> AppConfig:
    """Precedence: BTC_NETWORK env > explicit file arg > cwd file > home file > defaults."""
    merged: dict[str, Any] = {}
    for p in config_file_candidates(config_path):
        merged.update(_safe_load_yaml(p))

    net = os.environ.get("BTC_NETWORK") or os.environ.get("BTC_PURE_NETWORK")
    if net in ("mainnet", "testnet"):
        merged["network"] = net
    elif "network" not in merged:
        merged["network"] = "testnet"

    peer_limit = merged.get("peer_limit", 16)
    try:
        pl = int(peer_limit)
    except (TypeError, ValueError):
        pl = 16

    n = merged.get("network", "testnet")
    if n not in ("mainnet", "testnet"):
        n = "testnet"

    return AppConfig(network=n, peer_limit=pl)
