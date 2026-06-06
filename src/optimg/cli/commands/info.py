from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from PIL import Image
from PIL.ExifTags import Base

from optimg.cli.app import app, console
from optimg.cli.output import _human_size


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
    with Image.open(source) as img:
        console.print(f"[bold cyan]File:[/bold cyan]       {source}")
        console.print(f"[bold cyan]Size:[/bold cyan]       {img.size[0]}x{img.size[1]} px")
        console.print(f"[bold cyan]Mode:[/bold cyan]       {img.mode}")
        console.print(f"[bold cyan]Format:[/bold cyan]     {img.format}")
        console.print(f"[bold cyan]File size:[/bold cyan]  {_human_size(source.stat().st_size)}")

        if img.format == "JPEG":
            console.print(
                f"[bold cyan]Progressive:[/bold cyan] {'Yes' if img.info.get('progressive') else 'No'}"
            )

        exif = img.getexif()
        if exif:
            console.print("\n[bold yellow]EXIF Metadata:[/bold yellow]")
            for tag_id, value in exif.items():
                tag = Base(tag_id).name if tag_id in {t.value for t in Base} else f"Tag {tag_id}"
                console.print(f"  {tag}: {value}")
        else:
            console.print("\n[bold yellow]EXIF Metadata:[/bold yellow] None")
