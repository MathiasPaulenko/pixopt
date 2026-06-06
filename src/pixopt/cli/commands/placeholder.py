"""placeholder command — extract dominant color, LQIP or blurhash."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from pixopt.cli.app import app, console
from pixopt.placeholder import generate_placeholder


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
        str,
        typer.Option(
            "--type",
            "-t",
            help="Placeholder type: color, lqip, blurhash.",
        ),
    ] = "color",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Write the placeholder to a file.",
        ),
    ] = None,
) -> None:
    """Generate a placeholder (dominant color, LQIP or blurhash) for lazy loading."""
    if placeholder_type not in ("color", "lqip", "blurhash"):
        console.print("[bold red]Invalid type. Use: color, lqip, or blurhash.[/bold red]")
        raise typer.Exit(1)

    result = generate_placeholder(
        source,
        placeholder_type=placeholder_type,  # type: ignore[arg-type]
    )

    console.print(f"[bold green]{placeholder_type.upper()}:[/bold green] {result}")

    if output is not None:
        output = output.resolve()
        output.write_text(result + "\n", encoding="utf-8")
        console.print(f"[bold green]Saved to[/bold green] {output}")
