"""Optimize command: resize, compress and convert images."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Annotated

import typer

from pixopt._units import BYTES_PER_KB
from pixopt.adaptive_quality import find_quality_for_target_size
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
    TargetSizeOption,
    WidthOption,
)
from pixopt.cli.output import _print_result, _print_summary
from pixopt.cli.preset_helpers import merge_preset
from pixopt.exif import EXIFGroup
from pixopt.image_ops import _open_image
from pixopt.models import Anchor, FitMode, OutputFormat
from pixopt.optimizer import optimize_directory, optimize_image
from pixopt.smart_format import detect_optimal_format
from pixopt.utils import validate_no_parent_references


def _parse_exif_groups(groups: list[str]) -> set[EXIFGroup]:
    """Parse a list of EXIF group name strings into a set of EXIFGroup enums."""
    result: set[EXIFGroup] = set()
    for g in groups:
        with contextlib.suppress(ValueError):
            result.add(EXIFGroup(g.lower()))
    return result


def _resolve_quality(
    source: Path,
    quality: int,
    target_size: int | None,
    fmt: OutputFormat,
    width: int | None,
    height: int | None,
    fit: FitMode | None,
    anchor: Anchor,
    aspect_ratio: str | None,
    background_color: str,
    strip: bool,
    progressive: bool,
    optimize_flag: bool,
    lossless: bool,
) -> int:
    if target_size is None or target_size <= 0:
        return quality
    try:
        with _open_image(source, label="source") as img:
            img.load()
            from pixopt.format_resolver import resolve_output_format

            _, pillow_fmt = resolve_output_format(img, source, fmt)
            if pillow_fmt not in ("JPEG", "WEBP"):
                return quality
            return find_quality_for_target_size(
                img,
                pillow_fmt,
                target_size * BYTES_PER_KB,
                max_width=width,
                max_height=height,
                fit=fit,
                anchor=anchor,
                aspect_ratio=aspect_ratio,
                background_color=background_color,
                strip_metadata=strip,
                progressive=progressive,
                optimize=optimize_flag,
                lossless=lossless,
            )
    except (OSError, ValueError):
        # ``optimize_image`` will produce a clean result with the missing/invalid
        # file details; use the requested quality as a fallback here.
        return quality


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
    fit: FitOption = None,
    anchor: AnchorOption = Anchor.CENTER,
    aspect_ratio: AspectRatioOption = None,
    background_color: BackgroundColorOption = "white",
    auto_orient: AutoOrientOption = None,
    target_size: TargetSizeOption = None,
    backup: BackupOption = None,
    min_size: MinSizeOption = None,
    preset: PresetOption = None,
    preset_file: PresetFileOption = None,
    output_fmt: OutputFormatOption = "table",
    keep_exif: Annotated[
        list[str] | None,
        typer.Option(
            "--keep-exif",
            help=(
                "EXIF groups to keep when stripping metadata "
                "(orientation, copyright, gps, camera, lens, exposure, date, software, thumbnail). "
                "Can be repeated."
            ),
        ),
    ] = None,
    smart_format: Annotated[
        bool,
        typer.Option(
            "--smart-format",
            help="Auto-detect the most efficient output format.",
        ),
    ] = False,
) -> None:
    """Optimize an image or all images in a directory."""
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

    # Extract merged values back into local variables.
    quality = p.get("quality", quality)
    strip = p.get("strip", strip)
    progressive = p.get("progressive", progressive)
    optimize_flag = p.get("optimize", optimize_flag)
    lossless = p.get("lossless", lossless)
    fit = FitMode(p["fit"]) if "fit" in p else fit
    anchor = Anchor(p["anchor"]) if "anchor" in p else anchor
    aspect_ratio = p.get("aspect-ratio", aspect_ratio)
    background_color = p.get("background-color", background_color)
    _merged_auto_orient = p.get("auto-orient", True)
    resolved_auto_orient: bool = (
        _merged_auto_orient if isinstance(_merged_auto_orient, bool) else True
    )
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
            auto_orient=resolved_auto_orient,
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
        resolved_quality = _resolve_quality(
            source,
            quality,
            target_size,
            resolved_fmt,
            width,
            height,
            fit,
            anchor,
            aspect_ratio,
            background_color,
            strip,
            progressive,
            optimize_flag,
            lossless,
        )
        if output is not None and (error := validate_no_parent_references(output, "output")):
            console.print(f"[bold red]{error}[/bold red]")
            raise typer.Exit(1)
        result = optimize_image(
            source,
            output,
            max_width=width,
            max_height=height,
            fit=fit,
            anchor=anchor,
            aspect_ratio=aspect_ratio,
            background_color=background_color,
            auto_orient=resolved_auto_orient,
            quality=resolved_quality,
            strip_metadata=strip,
            output_format=resolved_fmt,
            progressive=progressive,
            optimize=optimize_flag,
            overwrite=overwrite,
            lossless=lossless,
            backup_dir=backup,
            min_size_bytes=min_bytes,
            keep_exif_groups=_parse_exif_groups(keep_exif) if keep_exif else None,
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
