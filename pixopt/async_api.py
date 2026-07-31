"""Async API: non-blocking variants of core pixopt functions.

Provides ``async`` wrappers around the synchronous core functions so that
high-throughput pipelines and the MCP server can process images without
blocking the event loop.

CPU-bound work (Pillow operations) is dispatched to a thread pool via
``asyncio.to_thread`` so that the event loop remains responsive.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence
from pathlib import Path

from PIL import Image

from pixopt._units import WHITE
from pixopt.exif import EXIFGroup
from pixopt.inventory import ScanReport, scan_directory
from pixopt.io_bytes import Base64Result, BytesResult
from pixopt.models import (
    Anchor,
    BatchReport,
    FitMode,
    ImageInfo,
    OptimizationResult,
    OutputFormat,
)
from pixopt.optimizer import (
    optimize_image,
    validate_optimize_params,
)
from pixopt.perceptual import DuplicateReport, scan_duplicates
from pixopt.progress import ProgressCallback, ProgressInfo
from pixopt.utils import validate_no_parent_references

__all__ = [
    "async_optimize_image",
    "async_batch_optimize",
    "async_inspect_image",
    "async_scan_directory",
    "async_scan_duplicates",
    "async_optimize_bytes",
    "async_optimize_base64",
]


async def async_optimize_image(
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
    """Async variant of :func:`pixopt.optimize_image`.

    Runs the synchronous optimization in a background thread.
    """
    if error := validate_optimize_params(
        quality=quality,
        max_width=max_width,
        max_height=max_height,
        min_size_bytes=min_size_bytes,
    ):
        raise ValueError(error)
    return await asyncio.to_thread(
        optimize_image,
        source,
        output,
        max_width=max_width,
        max_height=max_height,
        quality=quality,
        strip_metadata=strip_metadata,
        output_format=output_format,
        keep_aspect_ratio=keep_aspect_ratio,
        fit=fit,
        anchor=anchor,
        aspect_ratio=aspect_ratio,
        background_color=background_color,
        auto_orient=auto_orient,
        progressive=progressive,
        optimize=optimize,
        overwrite=overwrite,
        lossless=lossless,
        backup_dir=backup_dir,
        min_size_bytes=min_size_bytes,
        keep_exif_groups=keep_exif_groups,
    )


async def async_batch_optimize(
    sources: Sequence[Path | str],
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
    max_concurrency: int = 4,
    on_progress: ProgressCallback | None = None,
) -> BatchReport:
    """Async variant of :func:`pixopt.batch_optimize`.

    Processes images concurrently using ``max_concurrency`` parallel tasks,
    each running in a background thread.

    Args:
        sources: List of source image paths.
        output_dir: Output directory for optimized images.
        max_concurrency: Maximum number of images to process in parallel.
        on_progress: Optional progress callback.

    Returns:
        A :class:`BatchReport` with aggregated results.

    """
    import time

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

    if max_concurrency <= 0:
        raise ValueError(f"max_concurrency must be positive, got {max_concurrency}")

    source_list = list(sources)
    total = len(source_list)

    start = time.perf_counter()
    results: list[OptimizationResult | None] = [None] * total

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _process_one(idx: int, src: Path | str) -> None:
        src_path = Path(src)
        out_path = out_dir / src_path.name
        try:
            async with semaphore:
                result = await async_optimize_image(
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
                    fit=fit,
                    anchor=anchor,
                    aspect_ratio=aspect_ratio,
                    background_color=background_color,
                    auto_orient=auto_orient,
                    keep_exif_groups=keep_exif_groups,
                    overwrite=overwrite,
                    lossless=lossless,
                    backup_dir=backup_dir,
                    min_size_bytes=min_size_bytes,
                )
            results[idx] = result
        except (OSError, ValueError, Image.DecompressionBombError, RuntimeError) as exc:
            result = OptimizationResult(
                source_path=src_path,
                output_path=out_path,
                original_size=0,
                optimized_size=0,
                savings_bytes=0,
                savings_percent=0.0,
                width=0,
                height=0,
                format="",
                metadata_removed=False,
                success=False,
                error=f"{exc}",
            )
            results[idx] = result
        if on_progress is not None:
            await asyncio.get_running_loop().run_in_executor(
                None,
                on_progress,
                ProgressInfo(
                    current=idx + 1,
                    total=total,
                    current_file=src_path,
                    success=result.success,
                    message=result.error or "",
                ),
            )

    tasks = [asyncio.create_task(_process_one(i, src)) for i, src in enumerate(source_list)]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    for i, value in enumerate(gathered):
        if isinstance(value, BaseException) and not isinstance(value, Exception):
            raise value
        if isinstance(value, Exception):
            if results[i] is not None:
                raise value
            src_path = Path(source_list[i])
            out_path = out_dir / src_path.name
            results[i] = OptimizationResult(
                source_path=src_path,
                output_path=out_path,
                original_size=0,
                optimized_size=0,
                savings_bytes=0,
                savings_percent=0.0,
                width=0,
                height=0,
                format="",
                metadata_removed=False,
                success=False,
                error=str(value),
            )

    elapsed = time.perf_counter() - start

    # Build the BatchReport from results
    valid_results = [r for r in results if r is not None]
    return _build_batch_report(valid_results, total, elapsed)


async def async_inspect_image(source: Path | str) -> ImageInfo:
    """Async variant of :func:`pixopt.inspect_image`.

    Runs image inspection in a background thread.
    """
    from pixopt.inspect import inspect_image

    return await asyncio.to_thread(inspect_image, source)


async def async_scan_directory(
    directory: Path | str,
    *,
    recursive: bool = False,
    extensions: Iterable[str] | None = None,
) -> ScanReport:
    """Async variant of :func:`pixopt.scan_directory`.

    Runs directory scan in a background thread.
    """
    return await asyncio.to_thread(
        scan_directory,
        directory,
        recursive=recursive,
        extensions=extensions,
    )


async def async_scan_duplicates(
    directory: Path | str,
    *,
    algorithm: str = "phash",
    threshold: int = 5,
    recursive: bool = True,
    hash_size: int = 8,
) -> DuplicateReport:
    """Async variant of :func:`pixopt.scan_duplicates`.

    Runs duplicate scan in a background thread.
    """
    return await asyncio.to_thread(
        scan_duplicates,
        directory,
        algorithm=algorithm,
        threshold=threshold,
        recursive=recursive,
        hash_size=hash_size,
    )


async def async_optimize_bytes(
    data: bytes,
    *,
    max_width: int | None = None,
    max_height: int | None = None,
    quality: int = 85,
    output_format: OutputFormat | str = OutputFormat.WEBP,
    progressive: bool = True,
    optimize: bool = True,
    strip_metadata: bool = True,
    lossless: bool = False,
    auto_orient: bool = True,
    fit: FitMode | str | None = None,
    anchor: Anchor | str = Anchor.CENTER,
    aspect_ratio: tuple[int, int] | str | None = None,
    background_color: tuple[int, int, int] | str = WHITE,
) -> BytesResult:
    """Async variant of :func:`pixopt.optimize_bytes`.

    Runs in-memory optimization in a background thread.
    """
    from pixopt.io_bytes import optimize_bytes

    return await asyncio.to_thread(
        optimize_bytes,
        data,
        max_width=max_width,
        max_height=max_height,
        quality=quality,
        output_format=output_format,
        progressive=progressive,
        optimize=optimize,
        strip_metadata=strip_metadata,
        lossless=lossless,
        auto_orient=auto_orient,
        fit=fit,
        anchor=anchor,
        aspect_ratio=aspect_ratio,
        background_color=background_color,
    )


async def async_optimize_base64(
    b64_str: str,
    *,
    max_width: int | None = None,
    max_height: int | None = None,
    quality: int = 85,
    output_format: OutputFormat | str = OutputFormat.WEBP,
    progressive: bool = True,
    optimize: bool = True,
    strip_metadata: bool = True,
    lossless: bool = False,
    auto_orient: bool = True,
    fit: FitMode | str | None = None,
    anchor: Anchor | str = Anchor.CENTER,
    aspect_ratio: tuple[int, int] | str | None = None,
    background_color: tuple[int, int, int] | str = WHITE,
) -> Base64Result:
    """Async variant of :func:`pixopt.optimize_base64`.

    Runs in-memory base64 optimization in a background thread.
    """
    from pixopt.io_bytes import optimize_base64

    return await asyncio.to_thread(
        optimize_base64,
        b64_str,
        max_width=max_width,
        max_height=max_height,
        quality=quality,
        output_format=output_format,
        progressive=progressive,
        optimize=optimize,
        strip_metadata=strip_metadata,
        lossless=lossless,
        auto_orient=auto_orient,
        fit=fit,
        anchor=anchor,
        aspect_ratio=aspect_ratio,
        background_color=background_color,
    )


def _build_batch_report(
    results: list[OptimizationResult],
    total: int,
    elapsed: float,
) -> BatchReport:
    """Build a BatchReport from a list of OptimizationResults."""
    from pixopt.models import BatchReport

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    total_original = sum(r.original_size for r in results)
    total_optimized = sum(r.optimized_size for r in successful)
    total_savings = total_original - total_optimized
    savings_pct = (total_savings / total_original * 100.0) if total_original > 0 else 0.0

    return BatchReport(
        total_files=total,
        succeeded=len(successful),
        failed=len(failed),
        total_original_size=total_original,
        total_optimized_size=total_optimized,
        total_savings_bytes=total_savings,
        total_savings_percent=savings_pct,
        elapsed_seconds=elapsed,
        results=results,
    )
