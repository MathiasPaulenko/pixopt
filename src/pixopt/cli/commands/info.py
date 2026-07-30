"""Info command: inspect image metadata without optimizing."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import Base

from pixopt.cli.app import app, console
from pixopt.cli.output import _human_size

_EXIF_TAG_IDS = {t.value for t in Base}


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
) -> None:
    """Show image metadata and properties without optimizing."""
    try:
        with Image.open(source) as img:
            console.print(f"[bold cyan]File:[/bold cyan]       {source}")
            console.print(f"[bold cyan]Size:[/bold cyan]       {img.size[0]}x{img.size[1]} px")
            console.print(f"[bold cyan]Mode:[/bold cyan]       {img.mode}")
            console.print(f"[bold cyan]Format:[/bold cyan]     {img.format}")
            size_str = _human_size(source.stat().st_size)
            console.print(f"[bold cyan]File size:[/bold cyan]  {size_str}")

            if img.format == "JPEG":
                prog = "Yes" if img.info.get("progressive") else "No"
                console.print(f"[bold cyan]Progressive:[/bold cyan] {prog}")

            exif = img.getexif()
            if exif:
                console.print("\n[bold yellow]EXIF Metadata:[/bold yellow]")
                for tag_id, value in exif.items():
                    tag = Base(tag_id).name if tag_id in _EXIF_TAG_IDS else f"Tag {tag_id}"
                    console.print(f"  {tag}: {value}")
            else:
                console.print("\n[bold yellow]EXIF Metadata:[/bold yellow] None")
    except UnidentifiedImageError as exc:
        console.print(f"[bold red]Cannot identify image file:[/bold red] {source}")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[bold red]Error reading {source}:[/bold red] {exc}")
        raise typer.Exit(1) from exc
