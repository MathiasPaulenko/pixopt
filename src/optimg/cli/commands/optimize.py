from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from PIL import Image

from optimg.adaptive_quality import find_quality_for_target_size
from optimg.cli.app import app, console
from optimg.cli.options import (
    BackupOption,
    FormatChoices,
    HeightOption,
    LosslessOption,
    MinSizeOption,
    OptimizeOption,
    OverwriteOption,
    ProgressiveOption,
    QualityOption,
    RecursiveOption,
    StripOption,
    TargetSizeOption,
    WidthOption,
)
from optimg.cli.output import _print_result, _print_summary
from optimg.models import OutputFormat
from optimg.optimizer import optimize_directory, optimize_image
from optimg.smart_format import detect_optimal_format


def _resolve_quality(
    source: Path,
    quality: int,
    target_size: int | None,
    fmt: OutputFormat,
    width: int | None,
    height: int | None,
    strip: bool,
    progressive: bool,
    optimize_flag: bool,
    lossless: bool,
) -> int:
    if target_size is None or target_size <= 0:
        return quality
    with Image.open(source) as img:
        img.load()
        from optimg.format_resolver import resolve_output_format
        _, pillow_fmt = resolve_output_format(img, source, fmt)
        if pillow_fmt not in ("JPEG", "WEBP"):
            return quality
        return find_quality_for_target_size(
            img,
            pillow_fmt,
            target_size * 1024,
            max_width=width,
            max_height=height,
            strip_metadata=strip,
            progressive=progressive,
            optimize=optimize_flag,
            lossless=lossless,
        )


@app.command()
def optimize(
    source: Annotated[
        Path,
        typer.Argument(
            help="Source image file or directory.",
            exists=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Argument(
            help="Output path (file or directory).",
            exists=False,
        ),
    ] = None,
    width: WidthOption = None,
    height: HeightOption = None,
    quality: QualityOption = 85,
    fmt: FormatChoices = OutputFormat.AUTO,
    strip: StripOption = True,
    progressive: ProgressiveOption = True,
    optimize_flag: OptimizeOption = True,
    recursive: RecursiveOption = False,
    overwrite: OverwriteOption = False,
    lossless: LosslessOption = False,
    target_size: TargetSizeOption = None,
    backup: BackupOption = None,
    min_size: MinSizeOption = None,
    smart_format: Annotated[
        bool,
        typer.Option(
            "--smart-format",
            help="Auto-detect the most efficient output format.",
        ),
    ] = False,
) -> None:
    """Optimize an image or all images in a directory."""
    resolved_fmt = fmt
    if smart_format and not source.is_dir():
        detected = detect_optimal_format(source)
        resolved_fmt = detected
        console.print(f"[dim]Smart format detected: {detected.value}[/dim]")

    min_bytes = min_size * 1024 if min_size is not None else None

    if source.is_dir():
        if output is not None:
            output = output.resolve()
        results = optimize_directory(
            source,
            output,
            recursive=recursive,
            max_width=width,
            max_height=height,
            quality=quality,
            strip_metadata=strip,
            output_format=resolved_fmt,
            progressive=progressive,
            optimize=optimize_flag,
            lossless=lossless,
            backup_dir=backup,
            min_size_bytes=min_bytes,
        )
        _print_summary(results)
    else:
        resolved_quality = _resolve_quality(
            source,
            quality,
            target_size,
            resolved_fmt,
            width,
            height,
            strip,
            progressive,
            optimize_flag,
            lossless,
        )
        result = optimize_image(
            source,
            output,
            max_width=width,
            max_height=height,
            quality=resolved_quality,
            strip_metadata=strip,
            output_format=resolved_fmt,
            progressive=progressive,
            optimize=optimize_flag,
            overwrite=overwrite,
            lossless=lossless,
            backup_dir=backup,
            min_size_bytes=min_bytes,
        )
        _print_result(result)
