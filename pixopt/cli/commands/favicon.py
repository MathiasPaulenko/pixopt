"""Favicon command: generate multi-resolution ICO files."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from pixopt.cli.app import app, console
from pixopt.cli.output import _print_result
from pixopt.constants import DEFAULT_FAVICON_SIZES
from pixopt.optimizer import convert_to_favicon
from pixopt.utils import validate_no_parent_references


@app.command()
def favicon(
    source: Annotated[
        Path,
        typer.Argument(
            help="Source image file.",
            exists=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Argument(
            help="Output .ico path. Defaults to source name with .ico.",
            exists=False,
        ),
    ] = None,
    sizes: Annotated[
        list[int] | None,
        typer.Option(
            "--size",
            help="Square sizes to include in the ICO.",
        ),
    ] = None,
    keep_transparency: Annotated[
        bool,
        typer.Option(
            "--keep-transparency/--fill-background",
            help="Preserve alpha channel or fill with background color.",
        ),
    ] = True,
) -> None:
    """Convert an image to a multi-resolution favicon (.ico)."""
    if output is not None and (error := validate_no_parent_references(output, "output")):
        console.print(f"[bold red]{error}[/bold red]")
        raise typer.Exit(1)

    result = convert_to_favicon(
        source,
        output,
        sizes=sizes if sizes is not None else DEFAULT_FAVICON_SIZES.copy(),
        keep_transparency=keep_transparency,
    )
    _print_result(result)
    if not result.success:
        raise typer.Exit(1)
