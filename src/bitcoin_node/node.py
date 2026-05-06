"""Thin orchestration over DNS discovery + P2P relay."""

from __future__ import annotations

import asyncio

from bitcoin_node.p2p.constants import MAINNET_MAGIC, TESTNET_MAGIC
from bitcoin_node.p2p.dns_seeds import gather_peers
from bitcoin_node.p2p.peer import BitcoinPeer


async def relay_raw_transaction(
    network: str,
    raw_tx: bytes,
    *,
    host: str | None = None,
    port: int | None = None,
    relay_field: bool = False,
) -> None:
    """Open a connection, complete handshake, push `tx`, then idle briefly."""
    magic = TESTNET_MAGIC if network == "testnet" else MAINNET_MAGIC
    peer = BitcoinPeer(magic=magic, relay=relay_field)

    if host is None:
        peers = await gather_peers(network)
        if not peers:
            raise RuntimeError("DNS seeds returned no IPv4 peers — pass explicit --host/--port")
        host, port = peers[0]

    if port is None:
        port = 18333 if network == "testnet" else 8333

    await peer.connect(host, port)
    try:
        await peer.handshake()
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
) -> None:
    asyncio.run(relay_raw_transaction(network, raw_tx, host=host, port=port))
