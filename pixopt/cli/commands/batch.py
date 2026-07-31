"""Batch command: optimize multiple specific image files."""

from __future__ import annotations

import sys
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
    OutputFormatOption,
    ProgressiveOption,
    QualityOption,
    StripOption,
    WidthOption,
)
from pixopt.cli.output import _print_summary
from pixopt.models import OutputFormat
from pixopt.optimizer import batch_optimize
from pixopt.progress import ProgressInfo
from pixopt.utils import validate_no_parent_references


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
    ] = Path("./optimized"),
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
    output_fmt: OutputFormatOption = "table",
) -> None:
    """Optimize multiple image files at once and return an aggregated report."""
    if error := validate_no_parent_references(output_dir, "output_dir"):
        console.print(f"[bold red]{error}[/bold red]")
        raise typer.Exit(1)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    min_bytes = min_size * 1024 if min_size is not None else None

    use_progress = sys.stdout.isatty()
    if use_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Optimizing images...", total=len(sources))

            def _on_progress(info: ProgressInfo) -> None:
                progress.update(
                    task,
                    completed=info.current,
                    description=f"Optimizing {info.current_file.name}...",
                )

            report = batch_optimize(
                sources,
                output_dir,
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
                on_progress=_on_progress,
            )
    else:
        report = batch_optimize(
            sources,
            output_dir,
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

    if output_fmt == "json":
        import json

        console.print_json(json.dumps(report.to_dict(), default=str))
        return

    _print_summary(report.results)
    console.print(
        f"\n[bold]Batch Report:[/bold] "
        f"{report.succeeded}/{report.total_files} succeeded, "
        f"{report.failed} failed. "
        f"Saved {report.human_total_savings} ({report.total_savings_percent:.1f}%) "
        f"in {report.elapsed_seconds:.2f}s",
    )
    if report.failed:
        raise typer.Exit(1)
