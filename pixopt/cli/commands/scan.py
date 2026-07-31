"""Scan command: directory inventory and aggregate statistics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pixopt.cli.app import app, console
from pixopt.inventory import scan_directory

_JSON_FLAG = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Output scan results as JSON instead of a rich table.",
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


@app.command()
def scan(
    directory: Annotated[
        Path,
        typer.Argument(
            help="Directory to scan for images.",
            exists=True,
            file_okay=False,
            resolve_path=True,
        ),
    ],
    json_output: _JSON_FLAG = False,
    recursive: _RECURSIVE_FLAG = False,
) -> None:
    """Scan a directory and show image inventory with aggregate statistics."""
    try:
        report = scan_directory(directory, recursive=recursive)
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
    console.print(f"[bold cyan]Directory:[/bold cyan]       {report.directory}")
    console.print(f"[bold cyan]Total files:[/bold cyan]     {report.total_files}")
    console.print(f"[bold cyan]Valid images:[/bold cyan]    {report.valid_images}")
    console.print(f"[bold cyan]Errors:[/bold cyan]          {report.errors}")
    console.print(f"[bold cyan]Total size:[/bold cyan]      {report.human_total_size}")

    if report.formats:
        fmt_str = ", ".join(f"{k}: {v}" for k, v in sorted(report.formats.items()))
        console.print(f"[bold cyan]Formats:[/bold cyan]        {fmt_str}")

    if report.largest_file:
        console.print(
            f"[bold cyan]Largest:[/bold cyan]          {report.largest_file.name} "
            f"({report.largest_size / 1024:.1f} KB)",
        )
    if report.smallest_file:
        console.print(
            f"[bold cyan]Smallest:[/bold cyan]         {report.smallest_file.name} "
            f"({report.smallest_size / 1024:.1f} KB)",
        )

    # Per-file table
    if report.entries:
        from rich.table import Table

        table = Table(title="Image Inventory", show_lines=False)
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Format", style="yellow")
        table.add_column("Size", justify="right")
        table.add_column("Dimensions", justify="right")
        table.add_column("Mode")
        table.add_column("Alpha")
        table.add_column("Animated")

        for entry in report.entries:
            dims = f"{entry.width}x{entry.height}" if entry.width else "—"
            alpha = "Yes" if entry.has_alpha else "No"
            animated = f"Yes ({entry.frame_count})" if entry.is_animated else "No"
            if entry.error:
                dims = f"[red]Error: {entry.error[:30]}[/red]"
            table.add_row(
                entry.file_path.name,
                entry.format,
                entry.human_file_size,
                dims,
                entry.mode or "—",
                alpha,
                animated,
            )

        console.print(table)
