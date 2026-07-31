"""Watermark command: add text or image overlays to images."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pixopt.cli.app import app, console
from pixopt.cli.options import OutputFormatOption
from pixopt.utils import validate_no_parent_references
from pixopt.watermark import WatermarkPosition, add_image_watermark, add_text_watermark

_TextOption = Annotated[
    str | None,
    typer.Option(
        "--text",
        "-t",
        help="Text watermark content.",
    ),
]

_WatermarkImageOption = Annotated[
    Path | None,
    typer.Option(
        "--watermark-image",
        "-w",
        help="Path to watermark image (PNG with alpha recommended).",
        exists=True,
        resolve_path=True,
    ),
]

_PositionOption = Annotated[
    WatermarkPosition,
    typer.Option(
        "--position",
        "-p",
        help="Watermark position.",
        case_sensitive=False,
    ),
]

_OpacityOption = Annotated[
    float,
    typer.Option(
        "--opacity",
        help="Opacity 0.0–1.0. Default: 0.5.",
        min=0.0,
        max=1.0,
    ),
]

_PaddingOption = Annotated[
    int,
    typer.Option(
        "--padding",
        help="Pixel padding from edge. Default: 20.",
        min=0,
    ),
]

_FontSizeOption = Annotated[
    int,
    typer.Option(
        "--font-size",
        help="Font size for text watermark. Default: 36.",
        min=1,
    ),
]

_ScaleOption = Annotated[
    float | None,
    typer.Option(
        "--scale",
        help="Scale factor for image watermark relative to base width (e.g. 0.2).",
        min=0.01,
        max=1.0,
    ),
]

_FontPathOption = Annotated[
    Path | None,
    typer.Option(
        "--font-path",
        help="Path to TTF/OTF font file for text watermark.",
        exists=True,
        resolve_path=True,
    ),
]


@app.command()
def watermark(
    source: Annotated[
        Path,
        typer.Argument(
            help="Source image file.",
            exists=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Argument(
            help="Output image path.",
        ),
    ],
    text: _TextOption = None,
    watermark_image: _WatermarkImageOption = None,
    position: _PositionOption = WatermarkPosition.BOTTOM_RIGHT,
    opacity: _OpacityOption = 0.5,
    padding: _PaddingOption = 20,
    font_size: _FontSizeOption = 36,
    scale: _ScaleOption = None,
    font_path: _FontPathOption = None,
    output_fmt: OutputFormatOption = "table",
) -> None:
    """Add a text or image watermark to an image."""
    if error := validate_no_parent_references(output, "output"):
        console.print(f"[bold red]{error}[/bold red]")
        raise typer.Exit(1)

    if text is None and watermark_image is None:
        console.print("[bold red]Error:[/bold red] Provide either --text or --watermark-image.")
        raise typer.Exit(1)

    try:
        if text is not None:
            result = add_text_watermark(
                source,
                output,
                text,
                position=position,
                opacity=opacity,
                padding=padding,
                font_size=font_size,
                font_path=font_path,
            )
        else:
            result = add_image_watermark(
                source,
                output,
                watermark_image,  # type: ignore[arg-type]
                position=position,
                opacity=opacity,
                padding=padding,
                scale=scale,
            )
    except FileNotFoundError as exc:
        console.print(f"[bold red]File not found:[/bold red] {exc}")
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1) from exc

    if output_fmt == "json":
        console.print_json(json.dumps(result.to_dict(), default=str))
        return

    console.print(f"[bold green]Watermark added:[/bold green] {result.output_path}")
    console.print(f"  Type:      {result.watermark_type}")
    console.print(f"  Position:  {position.value}")
    console.print(f"  Opacity:   {opacity}")
    console.print(f"  Size:      {result.width}x{result.height} px")
