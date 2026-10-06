"""placeholder command — extract dominant color, LQIP or blurhash."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from pixopt._units import MAX_IMAGE_DIMENSION, MAX_QUALITY, MIN_QUALITY
from pixopt.cli.app import app, console
from pixopt.placeholder import PlaceholderType, generate_placeholder
from pixopt.utils import validate_no_parent_references


@app.command()
def placeholder(
    source: Annotated[
        Path,
        typer.Argument(
            help="Source image file.",
            exists=True,
            resolve_path=True,
        ),
    ],
    placeholder_type: Annotated[
        PlaceholderType,
        typer.Option(
            "--type",
            "-t",
            help="Placeholder type: color, lqip, blurhash.",
        ),
    ] = PlaceholderType.COLOR,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Write the placeholder to a file.",
        ),
    ] = None,
    lqip_size: Annotated[
        int,
        typer.Option(
            "--lqip-size",
            min=1,
            max=MAX_IMAGE_DIMENSION,
            help="LQIP thumbnail max dimension in pixels.",
        ),
    ] = 32,
    lqip_quality: Annotated[
        int,
        typer.Option(
            "--lqip-quality",
            min=MIN_QUALITY,
            max=MAX_QUALITY,
            help="LQIP JPEG quality (1-100).",
        ),
    ] = 20,
) -> None:
    """Generate a placeholder (dominant color, LQIP or blurhash) for lazy loading."""
    try:
        result = generate_placeholder(
            source,
            placeholder_type=placeholder_type,
            lqip_size=lqip_size,
            lqip_quality=lqip_quality,
        )
    except FileNotFoundError as exc:
        console.print(f"[bold red]File not found:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except (OSError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[bold green]{placeholder_type.value.upper()}:[/bold green] {result}")

    if output is not None:
        if error := validate_no_parent_references(output, "output"):
            console.print(f"[bold red]{error}[/bold red]")
            raise typer.Exit(1)
        output = output.resolve()
        output.write_text(result + "\n", encoding="utf-8")
        console.print(f"[bold green]Saved to[/bold green] {output}")
