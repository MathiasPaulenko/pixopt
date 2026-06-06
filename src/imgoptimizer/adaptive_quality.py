"""Adaptive quality finder using binary search to hit a target file size."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from imgoptimizer.image_ops import build_save_kwargs, convert_mode, resize_image


def find_quality_for_target_size(
    img: Image.Image,
    pillow_fmt: str,
    target_size: int,
    *,
    max_width: int | None = None,
    max_height: int | None = None,
    keep_aspect_ratio: bool = True,
    strip_metadata: bool = True,
    progressive: bool = True,
    optimize: bool = True,
    lossless: bool = False,
    min_quality: int = 1,
    max_quality: int = 100,
    tolerance: float = 0.05,
    max_iterations: int = 8,
) -> int:
    """Find the JPEG/WEBP quality that produces a file closest to target_size.

    Uses binary search over quality (1-100) and measures the actual encoded
    file size in memory. Returns the quality value that yields a size
    closest to but not exceeding the target.

    Args:
        img: Open PIL Image.
        pillow_fmt: Target Pillow format (JPEG or WEBP).
        target_size: Target file size in bytes.
        max_width, max_height, keep_aspect_ratio: Resize options.
        strip_metadata, progressive, optimize, lossless: Passed to build_save_kwargs.
        min_quality: Lowest quality to try.
        max_quality: Highest quality to try.
        tolerance: Fractional tolerance around target_size (e.g. 0.05 = 5%).
        max_iterations: Maximum binary-search iterations.

    Returns:
        Quality integer (1-100).
    """
    if pillow_fmt not in ("JPEG", "WEBP"):
        return 85

    working = img.copy()
    working = convert_mode(working, pillow_fmt)
    working = resize_image(
        working,
        max_width=max_width,
        max_height=max_height,
        keep_aspect_ratio=keep_aspect_ratio,
    )

    low = min_quality
    high = max_quality
    best_quality = low
    best_diff = float("inf")

    for _ in range(max_iterations):
        if low > high:
            break
        mid = (low + high) // 2

        buf = BytesIO()
        kwargs = build_save_kwargs(
            pillow_fmt,
            quality=mid,
            progressive=progressive,
            optimize=optimize,
            strip_metadata=strip_metadata,
            lossless=lossless,
        )
        working.save(buf, format=pillow_fmt, **kwargs)
        size = buf.tell()

        diff = abs(size - target_size)
        if diff < best_diff:
            best_diff = diff
            best_quality = mid

        # Within tolerance window?
        if abs(size - target_size) <= target_size * tolerance:
            best_quality = mid
            break

        if size > target_size:
            high = mid - 1
        else:
            low = mid + 1

    return best_quality
