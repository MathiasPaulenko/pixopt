"""Convert command: change image format or extension."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from pixopt.cli.app import app, console
from pixopt.cli.options import (
    AnchorOption,
    AspectRatioOption,
    AutoOrientOption,
    BackgroundColorOption,
    BackupOption,
    FitOption,
    FormatChoices,
    HeightOption,
    LosslessOption,
    MinSizeOption,
    OptimizeOption,
    OutputFormatOption,
    OverwriteOption,
    PresetFileOption,
    PresetOption,
    ProgressiveOption,
    QualityOption,
    RecursiveOption,
    StripOption,
    WidthOption,
)
from pixopt.cli.output import _print_result, _print_summary
from pixopt.cli.preset_helpers import merge_preset
from pixopt.models import Anchor, FitMode, OutputFormat
from pixopt.optimizer import change_extension, optimize_directory
from pixopt.smart_format import detect_optimal_format
from pixopt.utils import validate_no_parent_references


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
    fit: FitOption = None,
    anchor: AnchorOption = Anchor.CENTER,
    aspect_ratio: AspectRatioOption = None,
    background_color: BackgroundColorOption = "white",
    auto_orient: AutoOrientOption = None,
    backup: BackupOption = None,
    min_size: MinSizeOption = None,
    preset: PresetOption = None,
    preset_file: PresetFileOption = None,
    output_fmt: OutputFormatOption = "table",
    smart_format: Annotated[
        bool,
        typer.Option(
            "--smart-format",
            help="Auto-detect the most efficient output format.",
        ),
    ] = False,
) -> None:
    """Convert image(s) to a different format or extension."""
    # Merge preset values with explicit CLI args (explicit wins).
    p = merge_preset(
        preset,
        str(preset_file) if preset_file else None,
        {
            "quality": quality,
            "strip": strip,
            "progressive": progressive,
            "optimize": optimize_flag,
            "lossless": lossless,
            "fit": fit.value if fit else None,
            "anchor": anchor.value if anchor != Anchor.CENTER else None,
            "aspect-ratio": aspect_ratio,
            "background-color": background_color if background_color != "white" else None,
            "auto-orient": auto_orient,
            "max-width": width,
            "max-height": height,
        },
    )

    quality = p.get("quality", quality)
    strip = p.get("strip", strip)
    progressive = p.get("progressive", progressive)
    optimize_flag = p.get("optimize", optimize_flag)
    lossless = p.get("lossless", lossless)
    fit = FitMode(p["fit"]) if "fit" in p else fit
    anchor = Anchor(p["anchor"]) if "anchor" in p else anchor
    aspect_ratio = p.get("aspect-ratio", aspect_ratio)
    background_color = p.get("background-color", background_color)
    auto_orient = p.get("auto-orient", True)
    width = p.get("max-width", width)
    height = p.get("max-height", height)

    resolved_fmt = fmt
    if smart_format and not source.is_dir():
        detected = detect_optimal_format(source)
        resolved_fmt = detected
        console.print(f"[dim]Smart format detected: {detected.value}[/dim]")

    min_bytes = min_size * 1024 if min_size is not None else None

    if source.is_dir():
        if output is not None:
            if error := validate_no_parent_references(output, "output"):
                console.print(f"[bold red]{error}[/bold red]")
                raise typer.Exit(1)
            output = output.resolve()
        results = optimize_directory(
            source,
            output,
            recursive=recursive,
            max_width=width,
            max_height=height,
            fit=fit,
            anchor=anchor,
            aspect_ratio=aspect_ratio,
            background_color=background_color,
            auto_orient=auto_orient,
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
        if any(not r.success for r in results):
            raise typer.Exit(1)
        if output_fmt == "json":
            import json as _json

            console.print_json(
                _json.dumps(
                    [
                        r.__dict__
                        | {"source_path": str(r.source_path), "output_path": str(r.output_path)}
                        for r in results
                    ],
                    default=str,
                )
            )
    else:
        if output is not None and (error := validate_no_parent_references(output, "output")):
            console.print(f"[bold red]{error}[/bold red]")
            raise typer.Exit(1)
        result = change_extension(
            source,
            output,
            max_width=width,
            max_height=height,
            fit=fit,
            anchor=anchor,
            aspect_ratio=aspect_ratio,
            background_color=background_color,
            auto_orient=auto_orient,
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
        if not result.success:
            raise typer.Exit(1)
        if output_fmt == "json":
            import json as _json

            console.print_json(
                _json.dumps(
                    result.__dict__
                    | {
                        "source_path": str(result.source_path),
                        "output_path": str(result.output_path),
                    },
                    default=str,
                )
            )
