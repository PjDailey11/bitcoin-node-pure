"""Bitcoin DNS seeds (TCP peer discovery)."""

from __future__ import annotations

import asyncio
import socket

TESTNET_SEEDS = (
    "testnet-seed.bitcoin.jonasschnelli.ch",
    "seed.testnet.bitcoin.sprovoost.nl",
    "testnet-seed.bluematt.me",
)

MAINNET_SEEDS = (
    "seed.bitcoin.sipa.be",
    "dnsseed.bluematt.me",
    "seed.bitcoinstats.com",
)


async def resolve_seed_hosts(hostname: str, port: int) -> list[tuple[str, int]]:
    """Resolve DNS seed to list of (ipv4_str, port)."""

    def _sync_resolve() -> list[tuple[str, int]]:
        out: list[tuple[str, int]] = []
        try:
            infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except OSError:
            return []
        for fam, _, _, _, sockaddr in infos:
            if fam == socket.AF_INET:
                host, prt = sockaddr[:2]
                out.append((host, prt))
        return out

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_resolve)


async def gather_peers(network: str = "testnet", limit: int = 16) -> list[tuple[str, int]]:
    seeds = TESTNET_SEEDS if network == "testnet" else MAINNET_SEEDS
    port = 18333 if network == "testnet" else 8333
    peers: list[tuple[str, int]] = []
    for seed in seeds:
        peers.extend(await resolve_seed_hosts(seed, port))
        if len(peers) >= limit:
            break
    return peers[:limit]
