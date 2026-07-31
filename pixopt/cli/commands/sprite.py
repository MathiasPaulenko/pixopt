"""Sprite command: combine images into a sprite or contact sheet."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pixopt._units import MAX_IMAGE_DIMENSION
from pixopt.cli.app import app, console
from pixopt.sprite import create_contact_sheet, create_sprite
from pixopt.utils import validate_no_parent_references

_JSON_FLAG = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Output results as JSON.",
    ),
]


@app.command()
def sprite(
    output: Annotated[
        Path,
        typer.Argument(
            help="Output sprite sheet path.",
            resolve_path=True,
        ),
    ],
    images: Annotated[
        list[Path],
        typer.Argument(
            help="Image files to combine into a sprite.",
            exists=True,
            resolve_path=True,
        ),
    ],
    cell_width: Annotated[
        int | None,
        typer.Option("--cell-width", help="Width of each cell in pixels."),
    ] = None,
    cell_height: Annotated[
        int | None,
        typer.Option("--cell-height", help="Height of each cell in pixels."),
    ] = None,
    columns: Annotated[
        int | None,
        typer.Option("--columns", "-c", help="Number of columns (grid layout)."),
    ] = None,
    layout: Annotated[
        str,
        typer.Option(
            "--layout",
            "-l",
            help="Layout: grid, horizontal, vertical.",
        ),
    ] = "grid",
    padding: Annotated[
        int,
        typer.Option(
            "--padding",
            "-p",
            min=0,
            max=MAX_IMAGE_DIMENSION,
            help="Pixels between cells.",
        ),
    ] = 0,
    contact_sheet: Annotated[
        bool,
        typer.Option(
            "--contact-sheet",
            help="Create a contact sheet with labels instead of a sprite.",
        ),
    ] = False,
    fmt: Annotated[
        str,
        typer.Option("--format", "-f", help="Output image format: PNG, JPEG, WEBP."),
    ] = "PNG",
    json_output: _JSON_FLAG = False,
) -> None:
    """Combine multiple images into a single sprite or contact sheet."""
    if error := validate_no_parent_references(output, "output"):
        console.print(f"[bold red]{error}[/bold red]")
        raise typer.Exit(1)

    for name, value in (
        ("cell_width", cell_width),
        ("cell_height", cell_height),
        ("columns", columns),
    ):
        if value is not None and (value < 1 or value > MAX_IMAGE_DIMENSION):
            console.print(
                f"[bold red]{name} must be between 1 and {MAX_IMAGE_DIMENSION}.[/bold red]"
            )
            raise typer.Exit(1)

    if layout not in ("grid", "horizontal", "vertical"):
        console.print("[bold red]Layout must be grid, horizontal, or vertical.[/bold red]")
        raise typer.Exit(1)

    try:
        if contact_sheet:
            result = create_contact_sheet(
                images,
                output,
                cell_width=cell_width or 200,
                cell_height=cell_height or 200,
                columns=columns,
                padding=padding,
                fmt=fmt,
            )
        else:
            result = create_sprite(
                images,
                output,
                cell_width=cell_width,
                cell_height=cell_height,
                columns=columns,
                layout=layout,
                padding=padding,
                fmt=fmt,
            )

        if json_output:
            console.print_json(json.dumps(result.to_dict(), default=str))
            return

        if result.success:
            console.print(f"[bold green]Sprite created:[/bold green] {result.output}")
            console.print(f"[bold cyan]Layout:[/bold cyan]        {result.layout}")
            console.print(f"[bold cyan]Columns:[/bold cyan]        {result.columns}")
            console.print(f"[bold cyan]Rows:[/bold cyan]           {result.rows}")
            console.print(
                f"[bold cyan]Cell size:[/bold cyan]      {result.cell_width}x{result.cell_height}"
            )
            console.print(f"[bold cyan]Sheet size:[/bold cyan]     {result.width}x{result.height}")
            console.print(f"[bold cyan]Total images:[/bold cyan]   {result.total_images}")
        else:
            console.print(f"[bold red]Error:[/bold red] {result.error}")
            raise typer.Exit(1)

    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc
