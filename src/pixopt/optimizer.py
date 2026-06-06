"""High-level optimization API."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from PIL import Image
from PIL.Image import Resampling

from pixopt.constants import DEFAULT_FAVICON_SIZES
from pixopt.image_ops import (
    build_save_kwargs,
    convert_mode,
    resize_image,
    resolve_and_adjust_path,
    strip_exif_post_process,
    strip_metadata_pillow,
)
from pixopt.models import OptimizationResult, OutputFormat
from pixopt.svg_optimizer import optimize_svg
from pixopt.utils import discover_images

# Register HEIC/HEIF support if pillow-heif is available
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass


def optimize_image(
    source: Path | str,
    output: Path | str | None = None,
    *,
    max_width: int | None = None,
    max_height: int | None = None,
    quality: int = 85,
    strip_metadata: bool = True,
    output_format: OutputFormat = OutputFormat.AUTO,
    keep_aspect_ratio: bool = True,
    progressive: bool = True,
    optimize: bool = True,
    overwrite: bool = False,
    lossless: bool = False,
    backup_dir: Path | str | None = None,
    min_size_bytes: int | None = None,
) -> OptimizationResult:
    """Optimize a single image.

    Args:
        source: Path to the source image.
        output: Path for the optimized image. If None, overwrites source (if overwrite=True).
        max_width: Maximum width in pixels. None means no resize.
        max_height: Maximum height in pixels. None means no resize.
        quality: JPEG/WEBP quality (1-100). Higher is better quality, larger file.
        strip_metadata: Remove EXIF and other metadata.
        output_format: Target format. AUTO infers from output path or original.
        keep_aspect_ratio: Maintain aspect ratio when resizing.
        progressive: Use progressive JPEG encoding.
        optimize: Enable Pillow optimization flags.
        overwrite: Allow overwriting the source file when output is None.
        lossless: Use lossless compression for PNG/WEBP. Ignored for JPEG.
        backup_dir: Directory to copy the original file into before processing.
        min_size_bytes: Skip files already smaller than this threshold (bytes).

    Returns:
        OptimizationResult with details of the operation.
    """
    source_path = Path(source)
    if not source_path.exists():
        return _error_result(source_path, f"File not found: {source_path}")

    original_size = source_path.stat().st_size

    if backup_dir is not None:
        backup = Path(backup_dir)
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, backup / source_path.name)

    if min_size_bytes is not None and original_size <= min_size_bytes:
        return OptimizationResult(
            source_path=source_path,
            output_path=source_path,
            original_size=original_size,
            optimized_size=original_size,
            savings_bytes=0,
            savings_percent=0.0,
            width=0,
            height=0,
            format="",
            metadata_removed=False,
            success=True,
            error=f"Skipped: file already below {min_size_bytes} bytes",
        )

    if output is None:
        if not overwrite:
            return _error_result(
                source_path,
                "Output path required unless overwrite=True",
                original_size=original_size,
            )
        output_path = source_path
    else:
        output_path = Path(output)

    # Handle SVG files with pure-Python optimizer
    if source_path.suffix.lower() == ".svg":
        return _optimize_svg(source_path, output_path, original_size)

    try:
        with Image.open(source_path) as img:
            img.load()
            output_path, pillow_fmt = resolve_and_adjust_path(
                img, output_path, output_format
            )

            is_animated = getattr(img, "is_animated", False) or getattr(img, "n_frames", 1) > 1
            is_gif_source = (img.format or "").upper() == "GIF"

            if is_animated and is_gif_source and pillow_fmt == "WEBP":
                return _optimize_animated_gif(
                    img,
                    source_path,
                    output_path,
                    original_size,
                    pillow_fmt,
                    max_width=max_width,
                    max_height=max_height,
                    keep_aspect_ratio=keep_aspect_ratio,
                    quality=quality,
                    strip_metadata=strip_metadata,
                    optimize=optimize,
                    lossless=lossless,
                )

            img = convert_mode(img, pillow_fmt)
            img = resize_image(
                img,
                max_width=max_width,
                max_height=max_height,
                keep_aspect_ratio=keep_aspect_ratio,
            )
            new_width, new_height = img.size

            save_kwargs = build_save_kwargs(
                pillow_fmt,
                quality=quality,
                progressive=progressive,
                optimize=optimize,
                strip_metadata=strip_metadata,
                lossless=lossless,
            )
            img = strip_metadata_pillow(img, pillow_fmt)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, format=pillow_fmt, **save_kwargs)

        if strip_metadata:
            strip_exif_post_process(output_path, pillow_fmt)

        optimized_size = output_path.stat().st_size
        savings = original_size - optimized_size

        return OptimizationResult(
            source_path=source_path,
            output_path=output_path,
            original_size=original_size,
            optimized_size=optimized_size,
            savings_bytes=savings,
            savings_percent=(savings / original_size * 100) if original_size > 0 else 0.0,
            width=new_width,
            height=new_height,
            format=pillow_fmt,
            metadata_removed=strip_metadata,
            success=True,
        )

    except Exception as exc:
        return _error_result(source_path, str(exc), original_size=original_size, output=output_path)


def _optimize_svg(
    source_path: Path,
    output_path: Path,
    original_size: int,
) -> OptimizationResult:
    """Optimize an SVG file using pure-Python minification."""
    try:
        raw = source_path.read_text(encoding="utf-8")
        optimized = optimize_svg(raw)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(optimized, encoding="utf-8")
        optimized_size = output_path.stat().st_size
        savings = original_size - optimized_size

        return OptimizationResult(
            source_path=source_path,
            output_path=output_path,
            original_size=original_size,
            optimized_size=optimized_size,
            savings_bytes=savings,
            savings_percent=(savings / original_size * 100) if original_size > 0 else 0.0,
            width=0,
            height=0,
            format="SVG",
            metadata_removed=True,
            success=True,
        )
    except Exception as exc:
        return _error_result(source_path, str(exc), original_size=original_size, output=output_path)


def _optimize_animated_gif(
    img: Image.Image,
    source_path: Path,
    output_path: Path,
    original_size: int,
    pillow_fmt: str,
    *,
    max_width: int | None = None,
    max_height: int | None = None,
    keep_aspect_ratio: bool = True,
    quality: int = 85,
    strip_metadata: bool = True,
    optimize: bool = True,
    lossless: bool = False,
) -> OptimizationResult:
    """Convert an animated GIF to animated WEBP frame-by-frame."""
    try:
        frames: list[Image.Image] = []
        for frame_idx in range(img.n_frames):
            img.seek(frame_idx)
            frame = img.copy()
            frame = convert_mode(frame, pillow_fmt)
            frame = resize_image(
                frame,
                max_width=max_width,
                max_height=max_height,
                keep_aspect_ratio=keep_aspect_ratio,
            )
            frame = strip_metadata_pillow(frame, pillow_fmt)
            frames.append(frame)

        save_kwargs = build_save_kwargs(
            pillow_fmt,
            quality=quality,
            optimize=optimize,
            strip_metadata=strip_metadata,
            animated=True,
            lossless=lossless,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(
            output_path,
            format=pillow_fmt,
            append_images=frames[1:],
            **save_kwargs,
        )

        optimized_size = output_path.stat().st_size
        savings = original_size - optimized_size

        return OptimizationResult(
            source_path=source_path,
            output_path=output_path,
            original_size=original_size,
            optimized_size=optimized_size,
            savings_bytes=savings,
            savings_percent=(savings / original_size * 100) if original_size > 0 else 0.0,
            width=frames[0].width,
            height=frames[0].height,
            format=pillow_fmt,
            metadata_removed=strip_metadata,
            success=True,
        )
    except Exception as exc:
        return _error_result(source_path, str(exc), original_size=original_size, output=output_path)


def optimize_directory(
    source_dir: Path | str,
    output_dir: Path | str | None = None,
    *,
    recursive: bool = False,
    extensions: Iterable[str] | None = None,
    backup_dir: Path | str | None = None,
    min_size_bytes: int | None = None,
    **kwargs: object,
) -> list[OptimizationResult]:
    """Optimize all images in a directory.

    Args:
        source_dir: Directory containing images.
        output_dir: Destination directory. If None, overwrites in-place.
        recursive: Search subdirectories.
        extensions: File extensions to process. Defaults to common image types.
        backup_dir: Directory to copy originals into before processing.
        min_size_bytes: Skip files already smaller than this threshold (bytes).
        **kwargs: Passed to optimize_image.

    Returns:
        List of OptimizationResult for each processed file.
    """
    src = Path(source_dir)
    results: list[OptimizationResult] = []

    for file_path in discover_images(src, recursive=recursive, extensions=extensions):
        if output_dir is not None:
            rel = file_path.relative_to(src)
            out = Path(output_dir) / rel
        else:
            out = None

        result = optimize_image(
            file_path,
            out,
            overwrite=(output_dir is None),
            backup_dir=backup_dir,
            min_size_bytes=min_size_bytes,
            **kwargs,
        )
        results.append(result)

    return results


def change_extension(
    source: Path | str,
    output: Path | str | None = None,
    *,
    output_format: OutputFormat = OutputFormat.AUTO,
    backup_dir: Path | str | None = None,
    min_size_bytes: int | None = None,
    **kwargs: object,
) -> OptimizationResult:
    """Convert an image to a different file format / extension.

    This is a thin wrapper around optimize_image focused on format conversion.
    All other optimization parameters are forwarded.

    Args:
        source: Path to the source image.
        output: Destination path. If None, overwrites source (requires overwrite=True).
        output_format: Target format. Defaults to inferring from output path.
        backup_dir: Directory to copy originals into before processing.
        min_size_bytes: Skip files already smaller than this threshold (bytes).
        **kwargs: Passed to optimize_image.

    Returns:
        OptimizationResult with details of the conversion.
    """
    return optimize_image(
        source,
        output,
        output_format=output_format,
        backup_dir=backup_dir,
        min_size_bytes=min_size_bytes,
        **kwargs,
    )


def convert_to_favicon(
    source: Path | str,
    output: Path | str | None = None,
    *,
    sizes: list[int] | None = None,
    background: tuple[int, int, int] = (255, 255, 255),
    keep_transparency: bool = True,
) -> OptimizationResult:
    """Convert an image to a multi-resolution ICO favicon.

    Generates a .ico file containing multiple square resolutions suitable
    for browser tabs, bookmarks and high-DPI displays.

    Args:
        source: Path to the source image.
        output: Output .ico path. If None, uses source name with .ico extension.
        sizes: List of square sizes to include. Default: [16, 32, 48, 64, 128, 256].
        background: RGB fill for transparent images when keep_transparency=False.
        keep_transparency: Preserve alpha channel if present.

    Returns:
        OptimizationResult with details of the operation.
    """
    source_path = Path(source)
    if not source_path.exists():
        return _error_result(source_path, f"File not found: {source_path}")

    original_size = source_path.stat().st_size

    if output is None:
        output_path = source_path.with_suffix(".ico")
    else:
        output_path = Path(output)
        if not output_path.suffix:
            output_path = output_path.with_suffix(".ico")

    chosen_sizes = sizes if sizes is not None else DEFAULT_FAVICON_SIZES.copy()

    try:
        with Image.open(source_path) as img:
            img.load()
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            elif img.mode == "RGB":
                img = img.convert("RGBA")

            icons: list[Image.Image] = []
            for size in chosen_sizes:
                copy = img.copy()
                copy = copy.resize((size, size), Resampling.LANCZOS)
                if not keep_transparency:
                    bg = Image.new("RGB", (size, size), background)
                    bg.paste(copy, mask=copy.split()[3])
                    icons.append(bg)
                else:
                    icons.append(copy)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            icons[0].save(
                output_path,
                format="ICO",
                append_images=icons[1:],
            )

        optimized_size = output_path.stat().st_size
        savings = original_size - optimized_size
        max_size = max(chosen_sizes)

        return OptimizationResult(
            source_path=source_path,
            output_path=output_path,
            original_size=original_size,
            optimized_size=optimized_size,
            savings_bytes=savings,
            savings_percent=(savings / original_size * 100) if original_size > 0 else 0.0,
            width=max_size,
            height=max_size,
            format="ICO",
            metadata_removed=True,
            success=True,
        )

    except Exception as exc:
        return _error_result(
            source_path, str(exc), original_size=original_size, output=output_path
        )


def _error_result(
    source_path: Path,
    error: str,
    *,
    original_size: int = 0,
    output: Path | None = None,
) -> OptimizationResult:
    """Build a failed OptimizationResult."""
    return OptimizationResult(
        source_path=source_path,
        output_path=output or Path(""),
        original_size=original_size,
        optimized_size=0,
        savings_bytes=0,
        savings_percent=0.0,
        width=0,
        height=0,
        format="",
        metadata_removed=False,
        success=False,
        error=error,
    )
