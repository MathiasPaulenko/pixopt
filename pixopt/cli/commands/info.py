"""Info command: inspect image metadata without optimizing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from PIL import UnidentifiedImageError

from pixopt.cli.app import app, console
from pixopt.inspect import inspect_image

_JSON_FLAG = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Output metadata as JSON instead of a rich table.",
    ),
]


@app.command()
def info(
    source: Annotated[
        Path,
        typer.Argument(
            help="Image file to inspect.",
            exists=True,
            resolve_path=True,
        ),
    ],
    json_output: _JSON_FLAG = False,
) -> None:
    """Show structured image metadata and properties without optimizing."""
    try:
        info_data = inspect_image(source)
    except UnidentifiedImageError as exc:
        console.print(f"[bold red]Cannot identify image file:[/bold red] {source}")
        raise typer.Exit(1) from exc
    except FileNotFoundError as exc:
        console.print(f"[bold red]File not found:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Error reading {source}:[/bold red] {exc}")
        raise typer.Exit(1) from exc

    if json_output:
        console.print_json(json.dumps(info_data.to_dict(), default=str))
        return

    # Rich table output.
    console.print(f"[bold cyan]File:[/bold cyan]          {info_data.file_path}")
    console.print(f"[bold cyan]Format:[/bold cyan]        {info_data.format}")
    console.print(
        f"[bold cyan]Dimensions:[/bold cyan]    {info_data.width}x{info_data.height} px",
    )
    console.print(f"[bold cyan]Mode:[/bold cyan]          {info_data.mode}")
    console.print(f"[bold cyan]File size:[/bold cyan]     {info_data.human_file_size}")

    if info_data.dpi:
        console.print(
            f"[bold cyan]DPI:[/bold cyan]            {info_data.dpi[0]:.0f}x{info_data.dpi[1]:.0f}",
        )
    else:
        console.print("[bold cyan]DPI:[/bold cyan]            N/A")

    console.print(f"[bold cyan]Has alpha:[/bold cyan]     {'Yes' if info_data.has_alpha else 'No'}")
    console.print(
        f"[bold cyan]Animated:[/bold cyan]       {'Yes' if info_data.is_animated else 'No'}"
        + (f" ({info_data.frame_count} frames)" if info_data.is_animated else ""),
    )
    console.print(
        f"[bold cyan]ICC profile:[/bold cyan]   {'Yes' if info_data.icc_profile else 'No'}",
    )
    orientation = info_data.orientation if info_data.orientation else "None"
    console.print(f"[bold cyan]Orientation:[/bold cyan]   {orientation}")

    if info_data.exif:
        console.print("\n[bold yellow]EXIF Metadata:[/bold yellow]")
        for tag, value in info_data.exif.items():
            console.print(f"  {tag}: {value}")
    else:
        console.print("\n[bold yellow]EXIF Metadata:[/bold yellow] None")
