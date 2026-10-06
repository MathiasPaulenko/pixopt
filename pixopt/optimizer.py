"""High-level optimization API."""

from __future__ import annotations

from typing import Any

__all__ = [
    "batch_optimize",
    "change_extension",
    "convert_to_favicon",
    "optimize_directory",
    "optimize_image",
    "validate_optimize_params",
]

import shutil
from collections.abc import Iterable
from pathlib import Path

from PIL import Image
from PIL.Image import Resampling

from pixopt._units import (
    MAX_DIRECTORY_SCAN,
    MAX_FAVICON_SIZES,
    MAX_GIF_FRAMES,
    MAX_GIF_TOTAL_PIXELS,
    MAX_INPUT_BYTES,
    MAX_QUALITY,
    MIN_QUALITY,
    PERCENT,
    WHITE,
)
from pixopt.constants import DEFAULT_FAVICON_SIZES
from pixopt.exif import EXIFGroup
from pixopt.image_ops import (
    _open_image,
    apply_exif_orientation,
    build_save_kwargs,
    convert_mode,
    resize_image,
    resolve_and_adjust_path,
    strip_exif_post_process,
    strip_metadata_pillow,
)
from pixopt.logging import get_logger
from pixopt.models import Anchor, BatchReport, FitMode, OptimizationResult, OutputFormat
from pixopt.progress import ProgressCallback, ProgressInfo
from pixopt.svg_optimizer import optimize_svg
from pixopt.utils import discover_images, validate_no_parent_references

_logger = get_logger("optimizer")

# Register HEIC/HEIF support if pillow-heif is available
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass


def validate_optimize_params(
    *,
    quality: int,
    max_width: int | None,
    max_height: int | None,
    min_size_bytes: int | None,
) -> str | None:
    """Return an error message if any parameter is invalid, otherwise None."""
    if not MIN_QUALITY <= quality <= MAX_QUALITY:
        return f"quality must be between {MIN_QUALITY} and {MAX_QUALITY}, got {quality}"
    if max_width is not None and max_width <= 0:
        return f"max_width must be a positive integer, got {max_width}"
    if max_height is not None and max_height <= 0:
        return f"max_height must be a positive integer, got {max_height}"
    if min_size_bytes is not None and min_size_bytes < 0:
        return f"min_size_bytes must be non-negative, got {min_size_bytes}"
    return None


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
    fit: FitMode | str | None = None,
    anchor: Anchor | str = Anchor.CENTER,
    aspect_ratio: tuple[int, int] | str | None = None,
    background_color: tuple[int, int, int] | str = WHITE,
    auto_orient: bool = True,
    progressive: bool = True,
    optimize: bool = True,
    overwrite: bool = False,
    lossless: bool = False,
    backup_dir: Path | str | None = None,
    min_size_bytes: int | None = None,
    keep_exif_groups: set[EXIFGroup] | None = None,
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
        keep_aspect_ratio: Maintain aspect ratio when resizing (legacy when fit is None).
        fit: Resize fit mode: down, cover, contain, fill.
        anchor: Anchor point for cover/contain cropping and positioning.
        aspect_ratio: Target aspect ratio as '16:9' or (16, 9).
        background_color: RGB tuple or hex color for contain padding.
        auto_orient: Apply EXIF orientation before processing.
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

    if error := validate_no_parent_references(source_path, "source"):
        return _error_result(source_path, error)

    try:
        original_size = source_path.stat().st_size
    except FileNotFoundError:
        _logger.warning("File not found", extra={"operation": "optimize", "path": str(source_path)})
        return _error_result(source_path, f"File not found: {source_path}")
    except OSError as exc:
        return _error_result(source_path, f"Cannot access file: {exc}")

    if not isinstance(output_format, OutputFormat):
        _logger.warning(
            "Invalid output_format", extra={"operation": "optimize", "path": str(source_path)}
        )
        return _error_result(
            source_path,
            f"output_format must be an OutputFormat value, got {type(output_format).__name__}",
        )

    if validation_error := validate_optimize_params(
        quality=quality,
        max_width=max_width,
        max_height=max_height,
        min_size_bytes=min_size_bytes,
    ):
        return _error_result(source_path, validation_error)

    try:
        if isinstance(fit, str) and fit:
            fit = FitMode(fit)
        if isinstance(anchor, str):
            anchor = Anchor(anchor)
    except ValueError as exc:
        return _error_result(source_path, str(exc))

    if original_size > MAX_INPUT_BYTES:
        return _error_result(
            source_path,
            f"Input too large (max {MAX_INPUT_BYTES} bytes)",
            original_size=original_size,
        )

    if output is not None:
        out = Path(output)
        if error := validate_no_parent_references(out, "output"):
            return _error_result(source_path, error, original_size=original_size)

    if backup_dir is not None:
        backup = Path(backup_dir)
        if error := validate_no_parent_references(backup, "backup_dir"):
            return _error_result(source_path, error, original_size=original_size)
        try:
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, backup / source_path.name)
        except OSError as exc:
            return _error_result(
                source_path,
                f"Failed to create backup: {exc}",
                original_size=original_size,
            )

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

    output_path: Path
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
        image: Image.Image
        with _open_image(source_path, label="source") as opened_img:
            image = opened_img
            output_path, pillow_fmt = resolve_and_adjust_path(
                image,
                output_path,
                output_format,
            )

            is_animated = (
                getattr(image, "is_animated", False)
                or getattr(
                    image,
                    "n_frames",
                    1,
                )
                > 1
            )

            if is_animated and pillow_fmt in ("WEBP", "GIF"):
                return _optimize_animated_gif(
                    image,
                    source_path,
                    output_path,
                    original_size,
                    pillow_fmt,
                    max_width=max_width,
                    max_height=max_height,
                    keep_aspect_ratio=keep_aspect_ratio,
                    fit=fit,
                    anchor=anchor,
                    aspect_ratio=aspect_ratio,
                    background_color=background_color,
                    quality=quality,
                    strip_metadata=strip_metadata,
                    optimize=optimize,
                    lossless=lossless,
                )

            if auto_orient and not is_animated:
                image = apply_exif_orientation(image)

            img = convert_mode(image, pillow_fmt)
            img = resize_image(
                img,
                max_width=max_width,
                max_height=max_height,
                keep_aspect_ratio=keep_aspect_ratio,
                fit=fit,
                anchor=anchor,
                aspect_ratio=aspect_ratio,
                background_color=background_color,
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
            try:
                img.save(output_path, format=pillow_fmt, **save_kwargs)
            finally:
                img.close()

        if strip_metadata and keep_exif_groups is not None:
            # Selective EXIF: keep only specified groups.
            # First save without EXIF, then re-apply filtered EXIF from source.
            import piexif

            try:
                src_exif = piexif.load(str(source_path))
                from pixopt.exif import filter_exif

                filtered = filter_exif(src_exif, keep_exif_groups)
                has_data = any(
                    filtered.get(ifd) for ifd in ("0th", "Exif", "GPS", "1st", "Interoperability")
                ) or filtered.get("thumbnail")
                if has_data:
                    exif_bytes = piexif.dump(filtered)
                    # Re-save with filtered EXIF, keeping the same encoder
                    # settings so quality/optimize options are not lost.
                    resave_kwargs = {k: v for k, v in save_kwargs.items() if k != "exif"}
                    with Image.open(output_path) as _re:
                        _re.save(output_path, format=pillow_fmt, exif=exif_bytes, **resave_kwargs)
            except (OSError, ValueError, KeyError) as exc:
                _logger.warning("Failed to apply filtered EXIF", exc_info=exc)
        elif strip_metadata:
            strip_exif_post_process(output_path, pillow_fmt)

        optimized_size = output_path.stat().st_size
        savings = original_size - optimized_size

        return OptimizationResult(
            source_path=source_path,
            output_path=output_path,
            original_size=original_size,
            optimized_size=optimized_size,
            savings_bytes=savings,
            savings_percent=(savings / original_size * PERCENT) if original_size > 0 else 0.0,
            width=new_width,
            height=new_height,
            format=pillow_fmt,
            metadata_removed=strip_metadata,
            success=True,
        )

    except Image.DecompressionBombError as exc:
        return _error_result(
            source_path,
            f"Image too large or possible decompression bomb: {exc}",
            original_size=original_size,
            output=output_path,
        )
    except (OSError, ValueError) as exc:
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
            savings_percent=(savings / original_size * PERCENT) if original_size > 0 else 0.0,
            width=0,
            height=0,
            format="SVG",
            metadata_removed=True,
            success=True,
        )
    except (OSError, ValueError) as exc:
        _logger.error(
            "Optimization failed", extra={"operation": "optimize", "path": str(source_path)}
        )
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
    fit: FitMode | str | None = None,
    anchor: Anchor | str = Anchor.CENTER,
    aspect_ratio: tuple[int, int] | str | None = None,
    background_color: tuple[int, int, int] | str = WHITE,
    quality: int = 85,
    strip_metadata: bool = True,
    optimize: bool = True,
    lossless: bool = False,
) -> OptimizationResult:
    """Convert an animated image to animated WEBP/GIF frame-by-frame."""
    try:
        n_frames: int = getattr(img, "n_frames", 1)
        if n_frames > MAX_GIF_FRAMES:
            return _error_result(
                source_path,
                f"Animated image has too many frames (max {MAX_GIF_FRAMES}), got {n_frames}",
                original_size=original_size,
                output=output_path,
            )

        frames: list[Image.Image] = []
        durations: list[int] = []
        total_pixels = 0
        for frame_idx in range(n_frames):
            img.seek(frame_idx)
            durations.append(int(img.info.get("duration", 100)))
            frame = img.copy()
            try:
                frame = convert_mode(frame, pillow_fmt)
                frame = resize_image(
                    frame,
                    max_width=max_width,
                    max_height=max_height,
                    keep_aspect_ratio=keep_aspect_ratio,
                    fit=fit,
                    anchor=anchor,
                    aspect_ratio=aspect_ratio,
                    background_color=background_color,
                )
                frame = strip_metadata_pillow(frame, pillow_fmt)

                frame_pixels = frame.width * frame.height
                if total_pixels + frame_pixels > MAX_GIF_TOTAL_PIXELS:
                    for f in frames:
                        f.close()
                    frame.close()
                    return _error_result(
                        source_path,
                        f"Animated image exceeds maximum total pixel budget "
                        f"(max {MAX_GIF_TOTAL_PIXELS}), got {total_pixels + frame_pixels}",
                        original_size=original_size,
                        output=output_path,
                    )

                total_pixels += frame_pixels
                frames.append(frame)
            except (OSError, ValueError) as exc:
                for f in frames:
                    f.close()
                frame.close()
                return _error_result(
                    source_path,
                    str(exc),
                    original_size=original_size,
                    output=output_path,
                )

        save_kwargs = build_save_kwargs(
            pillow_fmt,
            quality=quality,
            optimize=optimize,
            strip_metadata=strip_metadata,
            animated=True,
            lossless=lossless,
        )
        if pillow_fmt in ("WEBP", "GIF"):
            save_kwargs["duration"] = durations
            save_kwargs["loop"] = int(img.info.get("loop", 0))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            frames[0].save(
                output_path,
                format=pillow_fmt,
                append_images=frames[1:],
                **save_kwargs,
            )
        finally:
            for frame in frames:
                frame.close()

        optimized_size = output_path.stat().st_size
        savings = original_size - optimized_size

        return OptimizationResult(
            source_path=source_path,
            output_path=output_path,
            original_size=original_size,
            optimized_size=optimized_size,
            savings_bytes=savings,
            savings_percent=(savings / original_size * PERCENT) if original_size > 0 else 0.0,
            width=frames[0].width,
            height=frames[0].height,
            format=pillow_fmt,
            metadata_removed=strip_metadata,
            success=True,
        )
    except (OSError, ValueError) as exc:
        _logger.error("Conversion failed", extra={"operation": "convert", "path": str(source_path)})
        return _error_result(source_path, str(exc), original_size=original_size, output=output_path)


def optimize_directory(
    source_dir: Path | str,
    output_dir: Path | str | None = None,
    *,
    recursive: bool = False,
    extensions: Iterable[str] | None = None,
    backup_dir: Path | str | None = None,
    min_size_bytes: int | None = None,
    on_progress: ProgressCallback | None = None,
    **kwargs: Any,
) -> list[OptimizationResult]:
    """Optimize all images in a directory.

    Args:
        source_dir: Directory containing images.
        output_dir: Destination directory. If None, overwrites in-place.
        recursive: Search subdirectories.
        extensions: File extensions to process. Defaults to common image types.
        backup_dir: Directory to copy originals into before processing.
        min_size_bytes: Skip files already smaller than this threshold (bytes).
        on_progress: Optional callback invoked after each file is processed.
        **kwargs: Passed to optimize_image.

    Returns:
        List of OptimizationResult for each processed file.

    """
    src = Path(source_dir)
    if output_dir is not None:
        out_dir_raw = Path(output_dir)
        if error := validate_no_parent_references(out_dir_raw, "output_dir"):
            raise ValueError(error)
        out_dir = out_dir_raw.resolve()
    else:
        out_dir = None
    if backup_dir is not None and (
        error := validate_no_parent_references(Path(backup_dir), "backup_dir")
    ):
        raise ValueError(error)
    results: list[OptimizationResult] = []

    files = list(discover_images(src, recursive=recursive, extensions=extensions))
    total = len(files)
    if total > MAX_DIRECTORY_SCAN:
        raise ValueError(f"Too many files in directory (max {MAX_DIRECTORY_SCAN}), got {total}")

    for idx, file_path in enumerate(files, 1):
        if out_dir is not None:
            try:
                rel = file_path.relative_to(src)
            except ValueError as exc:
                raise ValueError(f"File path is not inside source directory: {file_path}") from exc
            out = out_dir / rel
            if not out.resolve().is_relative_to(out_dir):
                raise ValueError(f"Output path escapes target directory: {out}")
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

        if on_progress is not None:
            on_progress(
                ProgressInfo(
                    current=idx,
                    total=total,
                    current_file=file_path,
                    success=result.success,
                    message=result.error or "",
                )
            )

    return results


def change_extension(
    source: Path | str,
    output: Path | str | None = None,
    *,
    output_format: OutputFormat = OutputFormat.AUTO,
    backup_dir: Path | str | None = None,
    min_size_bytes: int | None = None,
    **kwargs: Any,
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
    background: tuple[int, int, int] = WHITE,
    keep_transparency: bool = True,
    auto_orient: bool = True,
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
        auto_orient: Apply EXIF orientation before processing.

    Returns:
        OptimizationResult with details of the operation.

    """
    source_path = Path(source)
    try:
        original_size = source_path.stat().st_size
    except FileNotFoundError:
        return _error_result(source_path, f"File not found: {source_path}")
    except OSError as exc:
        return _error_result(source_path, f"Cannot access file: {exc}")

    if output is None:
        output_path = source_path.with_suffix(".ico")
    else:
        output_path = Path(output)
        if error := validate_no_parent_references(output_path, "output"):
            return _error_result(source_path, error, original_size=original_size)
        if not output_path.suffix:
            output_path = output_path.with_suffix(".ico")

    chosen_sizes = sizes if sizes is not None else DEFAULT_FAVICON_SIZES.copy()

    if not chosen_sizes:
        return _error_result(source_path, "sizes cannot be empty", original_size=original_size)

    if len(chosen_sizes) > MAX_FAVICON_SIZES:
        return _error_result(
            source_path,
            f"Too many favicon sizes (max {MAX_FAVICON_SIZES}), got {len(chosen_sizes)}",
            original_size=original_size,
        )

    for size in chosen_sizes:
        if size <= 0:
            return _error_result(
                source_path,
                f"favicon sizes must be positive integers, got {size!r}",
                original_size=original_size,
            )

    icons: list[Image.Image] = []
    image: Image.Image | None = None
    current_icon: Image.Image | None = None
    current_bg: Image.Image | None = None
    try:
        with _open_image(source_path, label="source") as opened_img:
            image = opened_img
            if auto_orient:
                image = apply_exif_orientation(image)
            # Work in RGBA so we can consistently composite on a background
            # when keep_transparency is False, regardless of the source mode.
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            for size in chosen_sizes:
                current_icon = image.resize((size, size), Resampling.LANCZOS)
                if not keep_transparency:
                    current_bg = Image.new("RGB", (size, size), background)
                    channels = current_icon.split()
                    if len(channels) < 4:
                        raise ValueError(
                            f"Icon resized to {size} has unexpected channel count: {len(channels)}"
                        )
                    current_bg.paste(current_icon, mask=channels[3])
                    for ch in channels:
                        ch.close()
                    icons.append(current_bg)
                    current_bg = None
                    current_icon.close()
                    current_icon = None
                else:
                    icons.append(current_icon)
                    current_icon = None

            output_path.parent.mkdir(parents=True, exist_ok=True)
            icons[0].save(
                output_path,
                format="ICO",
                append_images=icons[1:],
            )
    except (OSError, ValueError) as exc:
        _logger.error(
            "Favicon conversion failed", extra={"operation": "favicon", "path": str(source_path)}
        )
        return _error_result(
            source_path,
            str(exc),
            original_size=original_size,
            output=output_path,
        )
    finally:
        if current_icon is not None:
            current_icon.close()
        if current_bg is not None:
            current_bg.close()
        for icon in icons:
            icon.close()
        if image is not None:
            image.close()

    optimized_size = output_path.stat().st_size
    savings = original_size - optimized_size
    max_size = max(chosen_sizes)

    return OptimizationResult(
        source_path=source_path,
        output_path=output_path,
        original_size=original_size,
        optimized_size=optimized_size,
        savings_bytes=savings,
        savings_percent=(savings / original_size * PERCENT) if original_size > 0 else 0.0,
        width=max_size,
        height=max_size,
        format="ICO",
        metadata_removed=True,
        success=True,
    )


def _unique_output_path(out_dir: Path, name: str, used: set[str]) -> Path:
    """Return a collision-free output path inside *out_dir*.

    Two source files from different directories may share the same basename;
    later duplicates get a ``_1``, ``_2``, ... suffix so they do not overwrite
    each other's outputs.
    """
    candidate = name
    stem = Path(name).stem
    suffix = Path(name).suffix
    counter = 1
    while candidate in used:
        candidate = f"{stem}_{counter}{suffix}"
        counter += 1
    used.add(candidate)
    return out_dir / candidate


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


def batch_optimize(
    sources: Iterable[Path | str],
    output_dir: Path | str,
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
    fit: FitMode | str | None = None,
    anchor: Anchor | str = Anchor.CENTER,
    aspect_ratio: tuple[int, int] | str | None = None,
    background_color: tuple[int, int, int] | str = WHITE,
    auto_orient: bool = True,
    keep_exif_groups: set[EXIFGroup] | None = None,
    on_progress: ProgressCallback | None = None,
) -> BatchReport:
    """Optimize multiple image files and return an aggregated report.

    Args:
        sources: Iterable of source image paths.
        output_dir: Directory where all optimized images are written.

    Returns:
        A :class:`BatchReport` with totals, savings, failures and elapsed time.
    """
    import time

    from pixopt._units import PERCENT

    out_dir = Path(output_dir)
    if error := validate_no_parent_references(out_dir, "output_dir"):
        raise ValueError(error)
    out_dir.mkdir(parents=True, exist_ok=True)

    if error := validate_optimize_params(
        quality=quality,
        max_width=max_width,
        max_height=max_height,
        min_size_bytes=min_size_bytes,
    ):
        raise ValueError(error)

    source_list = list(sources)
    total = len(source_list)
    if total > MAX_DIRECTORY_SCAN:
        raise ValueError(f"Too many files in batch (max {MAX_DIRECTORY_SCAN}), got {total}")

    logger = get_logger("batch")
    logger.info("Batch optimization started", extra={"operation": "batch", "size_bytes": total})

    start = time.perf_counter()
    results: list[OptimizationResult] = []

    used_names: set[str] = set()
    for idx, src in enumerate(source_list, 1):
        src_path = Path(src)
        out_path = _unique_output_path(out_dir, src_path.name, used_names)
        result = optimize_image(
            src_path,
            out_path,
            max_width=max_width,
            max_height=max_height,
            quality=quality,
            strip_metadata=strip_metadata,
            output_format=output_format,
            keep_aspect_ratio=keep_aspect_ratio,
            progressive=progressive,
            optimize=optimize,
            overwrite=overwrite,
            lossless=lossless,
            backup_dir=backup_dir,
            min_size_bytes=min_size_bytes,
            fit=fit,
            anchor=anchor,
            aspect_ratio=aspect_ratio,
            background_color=background_color,
            auto_orient=auto_orient,
            keep_exif_groups=keep_exif_groups,
        )
        results.append(result)

        if on_progress is not None:
            on_progress(
                ProgressInfo(
                    current=idx,
                    total=total,
                    current_file=src_path,
                    success=result.success,
                    message=result.error or "",
                )
            )

    elapsed = time.perf_counter() - start

    total_files = len(results)
    succeeded = sum(1 for r in results if r.success)
    failed = total_files - succeeded
    total_original = sum(r.original_size for r in results)
    total_optimized = sum(r.optimized_size for r in results if r.success)
    total_savings = total_original - total_optimized
    savings_percent = (total_savings / total_original * PERCENT) if total_original > 0 else 0.0

    return BatchReport(
        results=results,
        total_files=total_files,
        succeeded=succeeded,
        failed=failed,
        total_original_size=total_original,
        total_optimized_size=total_optimized,
        total_savings_bytes=total_savings,
        total_savings_percent=savings_percent,
        elapsed_seconds=elapsed,
    )
