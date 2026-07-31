"""Duplicates command: find duplicate or near-duplicate images."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pixopt._units import MAX_HASH_SIZE
from pixopt.cli.app import app, console
from pixopt.perceptual import scan_duplicates

_JSON_FLAG = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Output results as JSON instead of a rich table.",
    ),
]

_RECURSIVE_FLAG = Annotated[
    bool,
    typer.Option(
        "--recursive",
        "-r",
        help="Scan subdirectories recursively.",
    ),
]

_ALGORITHM_OPT = Annotated[
    str,
    typer.Option(
        "--algorithm",
        "-a",
        help="Hash algorithm: phash, dhash, or ahash.",
    ),
]

_THRESHOLD_OPT = Annotated[
    int,
    typer.Option(
        "--threshold",
        "-t",
        min=0,
        max=MAX_HASH_SIZE * MAX_HASH_SIZE,
        help="Maximum Hamming distance for duplicates (0 = exact).",
    ),
]


@app.command()
def duplicates(
    directory: Annotated[
        Path,
        typer.Argument(
            help="Directory to scan for duplicates.",
            exists=True,
            file_okay=False,
            resolve_path=True,
        ),
    ],
    json_output: _JSON_FLAG = False,
    recursive: _RECURSIVE_FLAG = False,
    algorithm: _ALGORITHM_OPT = "phash",
    threshold: _THRESHOLD_OPT = 5,
) -> None:
    """Find duplicate or near-duplicate images in a directory."""
    if algorithm not in ("phash", "dhash", "ahash"):
        console.print("[bold red]Invalid algorithm. Use: phash, dhash, or ahash.[/bold red]")
        raise typer.Exit(1)

    try:
        report = scan_duplicates(
            directory,
            algorithm=algorithm,
            threshold=threshold,
            recursive=recursive,
        )
    except FileNotFoundError as exc:
        console.print(f"[bold red]Directory not found:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Error scanning {directory}:[/bold red] {exc}")
        raise typer.Exit(1) from exc

    if json_output:
        console.print_json(json.dumps(report.to_dict(), default=str))
        return

    # Summary
    console.print(f"[bold cyan]Directory:[/bold cyan]        {report.directory}")
    console.print(f"[bold cyan]Algorithm:[/bold cyan]        {report.algorithm}")
    console.print(f"[bold cyan]Threshold:[/bold cyan]        {report.threshold}")
    console.print(f"[bold cyan]Total files:[/bold cyan]      {report.total_files}")
    console.print(f"[bold cyan]Duplicate groups:[/bold cyan] {len(report.duplicate_groups)}")
    console.print(f"[bold cyan]Total duplicates:[/bold cyan] {report.total_duplicates}")

    if not report.has_duplicates:
        console.print("\n[green]No duplicates found.[/green]")
        return

    # Per-group table
    from rich.table import Table

    table = Table(title="Duplicate Groups", show_lines=False)
    table.add_column("Group", style="cyan", no_wrap=True)
    table.add_column("Files", style="yellow")
    table.add_column("Count", justify="right")

    for idx, group in enumerate(report.duplicate_groups, 1):
        file_names = "\n".join(f.name for f in group.files)
        table.add_row(f"#{idx}", file_names, str(group.count))

    console.print(table)
