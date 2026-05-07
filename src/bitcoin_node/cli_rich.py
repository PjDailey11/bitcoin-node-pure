"""Rich console helpers and styled CLI output."""

from __future__ import annotations

import json
from typing import Any


def try_import_rich() -> Any:
    try:
        from rich.console import Console
        from rich.padding import Padding
        from rich.panel import Panel
        from rich.syntax import Syntax
        from rich.table import Table
        from rich.text import Text

        return Console, Padding, Panel, Syntax, Table, Text
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("Install the 'rich' package: pip install rich") from e


def make_console(*, no_color: bool = False) -> Any:
    Console, _, _, _, _, _ = try_import_rich()
    return Console(force_terminal=True, no_color=no_color, highlight=False)


def print_banner(console: Any) -> None:
    """Binary-field Bitcoin logo: dim 0/1 background, bold bright logo body."""
    _, _, Panel, _, _, Text = try_import_rich()
    from rich import box

    from bitcoin_node.ascii_art import mask_rows

    rows = mask_rows()
    text_lines: list[Text] = []
    for ri, row in enumerate(rows):
        t = Text()
        for ci, cell in enumerate(row):
            bit = "1" if (ri + ci) % 2 else "0"
            if cell == "#":
                t.append(bit, style="bold bright_white")
            else:
                t.append(bit, style="dim white")
        text_lines.append(t)

    inner = Text()
    for i, tl in enumerate(text_lines):
        inner.append_text(tl)
        if i < len(text_lines) - 1:
            inner.append("\n")
    inner.append("\n\n")
    inner.append(
        "         educational node toolkit",
        style="italic dim white",
    )

    console.print(
        Panel(
            inner,
            title="[bold yellow]btc-pure[/]",
            subtitle="[dim]binary field banner[/]",
            border_style="bright_yellow",
            box=box.ASCII,
            padding=(1, 2, 1, 2),
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
    indent: int = 6,
    block_spacing: int = 2,
) -> None:
    _, Padding, _, Syntax, _, Text = try_import_rich()

    pad = (block_spacing, indent, block_spacing, indent)

    if format_json:
        js = json.dumps(payload_obj, indent=2, sort_keys=True)
        console.print(Padding(Syntax(js, "json", theme="monokai", word_wrap=True), pad))
        return

    def _block(title: str, value: str, *, value_style: str) -> None:
        blk = Text()
        blk.append(title + "\n", style="bold")
        blk.append(value, style=value_style)
        console.print(Padding(blk, pad))

    console.print()
    console.print()  # breathing room after banner

    if secret_hex:
        _block("secret_hex", secret_hex, value_style="bold red")
        console.print()

    _block("pubkey_compressed_hex", pubkey_hex, value_style="bold blue")
    console.print()
    _block("address_mainnet", main_a, value_style="green")
    console.print()
    _block("address_testnet", test_a, value_style="cyan")

    console.print()
    console.print()  # trailing space


def print_hex_line(console: Any, label: str, data: bytes) -> None:
    _, _, _, Syntax, _, _ = try_import_rich()
    console.print()
    console.print(f"[bold]{label}[/] ({len(data)} bytes)")
    console.print(Syntax(data.hex(), "text", word_wrap=True))
    console.print()
