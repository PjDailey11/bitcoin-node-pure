"""Rich console helpers and styled CLI output."""

from __future__ import annotations

import json
from typing import Any


def try_import_rich() -> Any:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax
        from rich.table import Table
        from rich.text import Text

        return Console, Panel, Syntax, Table, Text
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("Install the 'rich' package: pip install rich") from e


def make_console(*, no_color: bool = False) -> Any:
    Console, _, _, _, _ = try_import_rich()
    return Console(force_terminal=True, no_color=no_color, highlight=False)


def print_banner(console: Any, ascii_art: str) -> None:
    _, Panel, _, _, _ = try_import_rich()
    from rich import box

    console.print(
        Panel(
            ascii_art.strip("\n"),
            title="[bold]btc-pure[/]",
            border_style="bright_yellow",
            box=box.ASCII,
        )
    )


def print_key_material(
    console: Any,
    *,
    secret_hex: str | None,
    pubkey_hex: str,
    main_a: str,
    test_a: str,
    format_json: bool,
    payload_obj: dict[str, Any],
) -> None:
    _, _, Syntax, _, Text = try_import_rich()
    if format_json:
        js = json.dumps(payload_obj, indent=2, sort_keys=True)
        console.print(Syntax(js, "json", theme="monokai", word_wrap=True))
        return

    if secret_hex:
        console.print(Text("secret_hex:", style="bold"), end=" ")
        console.print(Syntax(secret_hex, "text", theme="ansi_dark", word_wrap=True), style="bold red")
    console.print(Text("pubkey_compressed_hex:", style="bold"), end=" ")
    console.print(Syntax(pubkey_hex, "text", theme="ansi_dark"), style="bold blue")
    console.print(Text("address_mainnet:", style="bold green"), end=" ")
    console.print(main_a, style="green")
    console.print(Text("address_testnet:", style="bold cyan"), end=" ")
    console.print(test_a, style="cyan")


def print_hex_line(console: Any, label: str, data: bytes) -> None:
    _, _, Syntax, _, _ = try_import_rich()
    console.print(f"[bold]{label}[/] ({len(data)} bytes)")
    console.print(Syntax(data.hex(), "text", word_wrap=True))
