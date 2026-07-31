"""Reusable Typer option type aliases."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer

from pixopt.image_ops import parse_color
from pixopt.models import Anchor, FitMode, OutputFormat

FitOption = Annotated[
    FitMode | None,
    typer.Option(
        "--fit",
        help="Resize fit mode: down, cover, contain, fill.",
        case_sensitive=False,
    ),
]

AnchorOption = Annotated[
    Anchor,
    typer.Option(
        "--anchor",
        "-a",
        help="Anchor point for cover/contain: center, top, face, etc.",
        case_sensitive=False,
    ),
]

_ASPECT_RATIO_RE = re.compile(r"^\d+[:/]\d+$")


def _validate_aspect_ratio(value: str | None) -> str | None:
    if value is None:
        return None
    if not _ASPECT_RATIO_RE.match(value):
        raise typer.BadParameter("aspect ratio must be in the form 'W:H' or 'W/H'")
    return value


AspectRatioOption = Annotated[
    str | None,
    typer.Option(
        "--aspect-ratio",
        "--ar",
        help="Target aspect ratio, e.g. '16:9' or '4/3'.",
        callback=_validate_aspect_ratio,
    ),
]


def _validate_background_color(value: str) -> str:
    try:
        parse_color(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    return value


BackgroundColorOption = Annotated[
    str,
    typer.Option(
        "--background-color",
        "--bg",
        help="Background color for contain padding, e.g. 'white' or '#ffffff'.",
        callback=_validate_background_color,
    ),
]

AutoOrientOption = Annotated[
    bool | None,
    typer.Option(
        "--auto-orient/--keep-orientation",
        help="Apply EXIF orientation before processing (default: True).",
    ),
]


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
        min=1,
        help="Maximum width in pixels.",
    ),
]

HeightOption = Annotated[
    int | None,
    typer.Option(
        "--height",
        "-h",
        min=1,
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
        min=1,
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
        min=1,
        help="Skip files already smaller than this threshold (KB).",
    ),
]

PresetOption = Annotated[
    str | None,
    typer.Option(
        "--preset",
        "-p",
        help="Apply a named preset: web, social, thumbnail, e-commerce, print.",
        case_sensitive=False,
    ),
]

PresetFileOption = Annotated[
    Path | None,
    typer.Option(
        "--preset-file",
        help="Load custom presets from a JSON file (use with --preset).",
        exists=True,
        resolve_path=True,
    ),
]


def _validate_output_format(value: str) -> str:
    value = value.lower()
    if value not in ("json", "table"):
        raise typer.BadParameter("output format must be 'json' or 'table'")
    return value


OutputFormatOption = Annotated[
    str,
    typer.Option(
        "--output",
        help="Output format: 'json' for JSON, 'table' for rich table (default).",
        case_sensitive=False,
        callback=_validate_output_format,
    ),
]
