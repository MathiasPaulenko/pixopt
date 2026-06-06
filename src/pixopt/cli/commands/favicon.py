from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from pixopt.cli.app import app
from pixopt.cli.output import _print_result
from pixopt.optimizer import convert_to_favicon


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
        list[int],
        typer.Option(
            "--size",
            help="Square sizes to include in the ICO.",
        ),
    ] = [16, 32, 48, 64, 128, 256],
    keep_transparency: Annotated[
        bool,
        typer.Option(
            "--keep-transparency/--fill-background",
            help="Preserve alpha channel or fill with background color.",
        ),
    ] = True,
) -> None:
    """Convert an image to a multi-resolution favicon (.ico)."""
    result = convert_to_favicon(
        source,
        output,
        sizes=sizes,
        keep_transparency=keep_transparency,
    )
    _print_result(result)
