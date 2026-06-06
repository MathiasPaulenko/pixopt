"""Reusable Typer option type aliases."""

from __future__ import annotations

from typing import Annotated

import typer

from optimg.models import OutputFormat

FormatChoices = Annotated[
    OutputFormat,
    typer.Option(
        "--format",
        "-f",
        help="Output image format.",
        case_sensitive=False,
    ),
]

QualityOption = Annotated[
    int,
    typer.Option(
        "--quality",
        "-q",
        min=1,
        max=100,
        help="JPEG/WEBP quality (1-100). Higher is better quality.",
    ),
]

StripOption = Annotated[
    bool,
    typer.Option(
        "--strip/--keep-metadata",
        "-s/-k",
        help="Remove EXIF and metadata to save space.",
    ),
]

ProgressiveOption = Annotated[
    bool,
    typer.Option(
        "--progressive/--baseline",
        help="Use progressive JPEG encoding.",
    ),
]

OptimizeOption = Annotated[
    bool,
    typer.Option(
        "--optimize/--no-optimize",
        help="Enable Pillow optimizer.",
    ),
]

WidthOption = Annotated[
    int | None,
    typer.Option(
        "--width",
        "-w",
        help="Maximum width in pixels.",
    ),
]

HeightOption = Annotated[
    int | None,
    typer.Option(
        "--height",
        "-h",
        help="Maximum height in pixels.",
    ),
]

RecursiveOption = Annotated[
    bool,
    typer.Option(
        "--recursive",
        "-r",
        help="Process directories recursively.",
    ),
]

OverwriteOption = Annotated[
    bool,
    typer.Option(
        "--overwrite",
        help="Overwrite source files when no output is given.",
    ),
]

LosslessOption = Annotated[
    bool,
    typer.Option(
        "--lossless",
        help="Use lossless compression for PNG/WEBP. Ignored for JPEG.",
    ),
]

TargetSizeOption = Annotated[
    int | None,
    typer.Option(
        "--target-size",
        help="Target file size in KB. Enables adaptive quality search.",
    ),
]

BackupOption = Annotated[
    Path | None,
    typer.Option(
        "--backup",
        help="Backup originals to this directory before processing.",
    ),
]

MinSizeOption = Annotated[
    int | None,
    typer.Option(
        "--min-size",
        help="Skip files already smaller than this threshold (KB).",
    ),
]
