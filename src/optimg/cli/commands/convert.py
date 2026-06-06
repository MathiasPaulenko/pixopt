from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

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
    WidthOption,
)
from optimg.cli.output import _print_result, _print_summary
from optimg.models import OutputFormat
from optimg.optimizer import change_extension, optimize_directory
from optimg.smart_format import detect_optimal_format


@app.command()
def convert(
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
    """Convert image(s) to a different format or extension."""
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
        result = change_extension(
            source,
            output,
            max_width=width,
            max_height=height,
            quality=quality,
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
