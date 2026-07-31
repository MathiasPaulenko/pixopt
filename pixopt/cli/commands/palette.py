"""Palette command: extract dominant colors from an image."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from pixopt.cli.app import app, console
from pixopt.palette import extract_palette

_JSON_FLAG = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Output palette as JSON.",
    ),
]

_CountOption = Annotated[
    int,
    typer.Option(
        "--count",
        "-n",
        help="Number of dominant colors to extract (1–32). Default: 6.",
        min=1,
        max=32,
    ),
]


@app.command()
def palette(
    source: Annotated[
        Path,
        typer.Argument(
            help="Source image file.",
            exists=True,
            resolve_path=True,
        ),
    ],
    count: _CountOption = 6,
    json_output: _JSON_FLAG = False,
) -> None:
    """Extract dominant colors from an image."""
    try:
        result = extract_palette(source, n=count)
    except FileNotFoundError as exc:
        console.print(f"[bold red]File not found:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except ValueError as exc:
        console.print(f"[bold red]Invalid argument:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc

    if json_output:
        console.print_json(json.dumps(result.to_dict(), default=str))
        return

    console.print(f"[bold cyan]Source:[/bold cyan]         {result.source_path}")
    console.print(
        f"[bold cyan]Dimensions:[/bold cyan]     {result.width}x{result.height} px",
    )
    console.print(f"[bold cyan]Colors:[/bold cyan]          {len(result.colors)}")

    if not result.colors:
        console.print("[dim]No colors extracted.[/dim]")
        return

    table = Table(title="Color Palette")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Hex", style="cyan")
    table.add_column("RGB", justify="center")
    table.add_column("Coverage", justify="right")
    table.add_column("Swatch", justify="center")

    for i, swatch in enumerate(result.colors, 1):
        r, g, b = swatch.rgb
        # Use rich's color block for a visual swatch.
        swatch_repr = f"[#{r:02x}{g:02x}{b:02x}]      [/#{r:02x}{g:02x}{b:02x}]"
        table.add_row(
            str(i),
            swatch.hex,
            f"rgb({r}, {g}, {b})",
            f"{swatch.percent:.1f}%",
            swatch_repr,
        )

    console.print(table)
