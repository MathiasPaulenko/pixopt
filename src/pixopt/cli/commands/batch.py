from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from pixopt.cli.app import app, console
from pixopt.cli.options import (
    BackupOption,
    FormatChoices,
    HeightOption,
    LosslessOption,
    MinSizeOption,
    OptimizeOption,
    ProgressiveOption,
    QualityOption,
    StripOption,
    WidthOption,
)
from pixopt.cli.output import _print_summary
from pixopt.models import OutputFormat
from pixopt.optimizer import optimize_image


@app.command()
def batch(
    sources: Annotated[
        list[Path],
        typer.Argument(
            help="Source image files.",
            exists=True,
            resolve_path=True,
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Output directory for all processed images.",
        ),
    ] = Path("./optimized"),  # type: ignore[assignment]
    width: WidthOption = None,
    height: HeightOption = None,
    quality: QualityOption = 85,
    fmt: FormatChoices = OutputFormat.AUTO,
    strip: StripOption = True,
    progressive: ProgressiveOption = True,
    optimize_flag: OptimizeOption = True,
    lossless: LosslessOption = False,
    backup: BackupOption = None,
    min_size: MinSizeOption = None,
) -> None:
    """Optimize multiple image files at once."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    min_bytes = min_size * 1024 if min_size is not None else None

    results: list[object] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Optimizing images...", total=len(sources))
        for src in sources:
            out = output_dir / src.name
            result = optimize_image(
                src,
                out,
                max_width=width,
                max_height=height,
                quality=quality,
                strip_metadata=strip,
                output_format=fmt,
                progressive=progressive,
                optimize=optimize_flag,
                lossless=lossless,
                backup_dir=backup,
                min_size_bytes=min_bytes,
            )
            results.append(result)
            progress.advance(task)

    _print_summary(results)  # type: ignore[arg-type]
