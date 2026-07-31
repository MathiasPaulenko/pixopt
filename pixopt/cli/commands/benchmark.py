"""Benchmark command: compare formats and quality levels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from pixopt.benchmark import benchmark_formats
from pixopt.cli.app import app, console

_JSON_FLAG = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Output benchmark results as JSON.",
    ),
]

_QualitiesOption = Annotated[
    list[int] | None,
    typer.Option(
        "--quality",
        "-q",
        help="Quality level(s) to benchmark (can be repeated). Default: 50,60,70,80,90.",
    ),
]

_FormatsOption = Annotated[
    list[str] | None,
    typer.Option(
        "--format",
        "-f",
        help="Format(s) to benchmark (can be repeated). Default: JPEG,WEBP,AVIF,PNG.",
        case_sensitive=False,
    ),
]


@app.command()
def benchmark(
    source: Annotated[
        Path,
        typer.Argument(
            help="Source image file to benchmark.",
            exists=True,
            resolve_path=True,
        ),
    ],
    qualities: _QualitiesOption = None,
    formats: _FormatsOption = None,
    json_output: _JSON_FLAG = False,
) -> None:
    """Benchmark an image across formats and quality levels."""
    try:
        result = benchmark_formats(
            source,
            qualities=qualities,
            formats=[f.upper() for f in formats] if formats else None,
        )
    except FileNotFoundError as exc:
        console.print(f"[bold red]File not found:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc

    if json_output:
        console.print_json(json.dumps(result.to_dict(), default=str))
        return

    # Rich table output.
    console.print(f"[bold cyan]Source:[/bold cyan]         {result.source_path}")
    console.print(f"[bold cyan]Format:[/bold cyan]         {result.source_format}")
    console.print(
        f"[bold cyan]Dimensions:[/bold cyan]     {result.width}x{result.height} px",
    )
    console.print(f"[bold cyan]Source size:[/bold cyan]    {result.human_source_size}")

    if not result.variants:
        console.print("[bold red]No variants could be generated.[/bold red]")
        return

    table = Table(title="Format Benchmark")
    table.add_column("Variant", style="cyan")
    table.add_column("Size", justify="right")
    table.add_column("Savings", justify="right")
    table.add_column("Recommended", justify="center")

    for v in result.variants:
        is_recommended = (
            v.format == result.recommended_format and v.quality == result.recommended_quality
        )
        marker = "[green]✓[/green]" if is_recommended else ""
        table.add_row(
            v.label,
            _human_size(v.size_bytes),
            f"{v.savings_percent:.1f}%",
            marker,
        )

    console.print(table)

    if result.recommended_format:
        console.print(
            f"\n[bold green]Recommended:[/bold green] "
            f"{result.recommended_format}"
            + (f" @ q{result.recommended_quality}" if result.recommended_quality else "")
            + f" — {result.human_recommended_size} "
            f"({result.recommended_savings:.1f}% savings)",
        )


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human readable string."""
    from pixopt._units import BYTES_PER_KB

    if size_bytes < BYTES_PER_KB:
        return f"{size_bytes} B"
    return f"{size_bytes / BYTES_PER_KB:.2f} KB"
