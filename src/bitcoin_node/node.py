"""Thin orchestration over DNS discovery + P2P relay."""

from __future__ import annotations

import asyncio

from collections.abc import Callable

from bitcoin_node.p2p.constants import MAINNET_MAGIC, TESTNET_MAGIC
from bitcoin_node.p2p.dns_seeds import gather_peers
from bitcoin_node.p2p.peer import BitcoinPeer

WireDebugFn = Callable[[str, bytes], None]


async def relay_raw_transaction(
    network: str,
    raw_tx: bytes,
    *,
    host: str | None = None,
    port: int | None = None,
    relay_field: bool = False,
    timeout: float = 20.0,
    dry_run: bool = False,
    wire_debug: WireDebugFn | None = None,
) -> None:
    """Open a connection, complete handshake, optionally push `tx`, then idle briefly."""
    magic = TESTNET_MAGIC if network == "testnet" else MAINNET_MAGIC
    peer = BitcoinPeer(magic=magic, relay=relay_field, wire_debug=wire_debug)

    if host is None:
        peers = await gather_peers(network)
        if not peers:
            raise RuntimeError("DNS seeds returned no IPv4 peers — pass explicit --host/--port")
        host, port = peers[0]

    if port is None:
        port = 18333 if network == "testnet" else 8333

    await peer.connect(host, port, timeout=timeout)
    try:
        await peer.handshake(timeout=timeout)
        if not dry_run:
            await peer.send_tx(raw_tx)
        await peer.drain_ping_pong()
    finally:
        await peer.close()


def relay_raw_transaction_sync(
    network: str,
    raw_tx: bytes,
    *,
    host: str | None = None,
    port: int | None = None,
    timeout: float = 20.0,
    dry_run: bool = False,
    wire_debug: WireDebugFn | None = None,
) -> None:
    asyncio.run(
        relay_raw_transaction(
            network,
            raw_tx,
            host=host,
            port=port,
            timeout=timeout,
            dry_run=dry_run,
            wire_debug=wire_debug,
        )
    )
