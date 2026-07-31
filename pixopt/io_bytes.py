"""Bytes and base64 I/O for image optimization.

Allow functions to accept ``bytes`` or base64 strings and return
``bytes``/base64.  Primarily for the MCP server, but also useful for
web backends.
"""

from __future__ import annotations

import base64 as _b64
import io
from dataclasses import dataclass
from typing import Any

from PIL import Image

from pixopt._units import (
    MAX_BASE64_LENGTH,
    MAX_IMAGE_DIMENSION,
    MAX_INPUT_BYTES,
    WHITE,
)
from pixopt.constants import FORMAT_MAP
from pixopt.image_ops import (
    apply_exif_orientation,
    build_save_kwargs,
    convert_mode,
    resize_image,
    strip_metadata_pillow,
)
from pixopt.logging import get_logger
from pixopt.models import Anchor, FitMode, OutputFormat

__all__ = [
    "Base64Result",
    "BytesResult",
    "optimize_bytes",
    "optimize_base64",
    "image_to_base64",
    "base64_to_image",
    "bytes_to_image",
    "image_to_bytes",
]

_logger = get_logger("io_bytes")


@dataclass
class BytesResult:
    """Result of an in-memory image optimization."""

    data: bytes
    format: str
    width: int
    height: int
    original_size: int
    optimized_size: int
    savings_bytes: int
    savings_percent: float
    success: bool
    error: str | None = None

    @property
    def human_original_size(self) -> str:
        from pixopt.models import _human_readable_size

        return _human_readable_size(self.original_size)

    @property
    def human_optimized_size(self) -> str:
        from pixopt.models import _human_readable_size

        return _human_readable_size(self.optimized_size)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "original_size": self.original_size,
            "optimized_size": self.optimized_size,
            "savings_bytes": self.savings_bytes,
            "savings_percent": self.savings_percent,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class Base64Result:
    """Result of an in-memory base64 image optimization."""

    base64: str | None
    format: str
    width: int
    height: int
    original_size: int
    optimized_size: int
    savings_bytes: int
    savings_percent: float
    success: bool
    error: str | None = None

    @property
    def human_original_size(self) -> str:
        from pixopt.models import _human_readable_size

        return _human_readable_size(self.original_size)

    @property
    def human_optimized_size(self) -> str:
        from pixopt.models import _human_readable_size

        return _human_readable_size(self.optimized_size)

    def to_dict(self) -> dict[str, Any]:
        return {
            "base64": self.base64,
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "original_size": self.original_size,
            "optimized_size": self.optimized_size,
            "savings_bytes": self.savings_bytes,
            "savings_percent": self.savings_percent,
            "success": self.success,
            "error": self.error,
        }


def bytes_to_image(data: bytes) -> Image.Image:
    """Convert raw image bytes into a PIL Image.

    Args:
        data: Raw image file bytes (JPEG, PNG, WEBP, etc.).

    Returns:
        A loaded :class:`PIL.Image.Image`.

    Raises:
        PIL.UnidentifiedImageError: If the bytes are not a valid image.
        ValueError: If the input exceeds the maximum allowed size.

    """
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError(f"Input too large (max {MAX_INPUT_BYTES} bytes)")
    with Image.open(io.BytesIO(data)) as img:
        img.load()
        return img


def image_to_bytes(
    img: Image.Image,
    *,
    fmt: str = "WEBP",
    quality: int = 85,
    progressive: bool = True,
    optimize: bool = True,
    strip_metadata: bool = True,
    lossless: bool = False,
) -> bytes:
    """Convert a PIL Image to raw bytes in the specified format.

    Args:
        img: The PIL Image to encode.
        fmt: Target Pillow format (e.g. ``"WEBP"``, ``"JPEG"``, ``"PNG"``).
        quality: JPEG/WEBP quality (1-100).
        progressive: Use progressive JPEG encoding.
        optimize: Enable Pillow optimization flags.
        strip_metadata: Remove EXIF and other metadata.
        lossless: Use lossless compression for PNG/WEBP.

    Returns:
        Raw image bytes in the target format.

    """
    save_kwargs = build_save_kwargs(
        fmt,
        quality=quality,
        progressive=progressive,
        optimize=optimize,
        strip_metadata=strip_metadata,
        lossless=lossless,
    )
    img = strip_metadata_pillow(img, fmt)
    with io.BytesIO() as buf:
        img.save(buf, format=fmt, **save_kwargs)
        return buf.getvalue()


def image_to_base64(
    img: Image.Image,
    *,
    fmt: str = "WEBP",
    quality: int = 85,
    progressive: bool = True,
    optimize: bool = True,
    strip_metadata: bool = True,
    lossless: bool = False,
) -> str:
    """Convert a PIL Image to a base64-encoded string.

    Args:
        img: The PIL Image to encode.
        fmt: Target Pillow format.
        quality: JPEG/WEBP quality (1-100).
        progressive: Use progressive JPEG encoding.
        optimize: Enable Pillow optimization flags.
        strip_metadata: Remove EXIF and other metadata.
        lossless: Use lossless compression for PNG/WEBP.

    Returns:
        A base64-encoded string of the image in the target format.

    """
    data = image_to_bytes(
        img,
        fmt=fmt,
        quality=quality,
        progressive=progressive,
        optimize=optimize,
        strip_metadata=strip_metadata,
        lossless=lossless,
    )
    return _b64.b64encode(data).decode("ascii")


def base64_to_image(b64_str: str) -> Image.Image:
    """Decode a base64-encoded string into a PIL Image.

    Args:
        b64_str: Base64-encoded image data.

    Returns:
        A loaded :class:`PIL.Image.Image`.

    Raises:
        PIL.UnidentifiedImageError: If the decoded bytes are not a valid image.
        ValueError: If the input exceeds the maximum allowed size.

    """
    if len(b64_str) > MAX_BASE64_LENGTH:
        raise ValueError(f"Base64 string too large (max {MAX_BASE64_LENGTH} characters)")
    data = _b64.b64decode(b64_str)
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError(f"Decoded input too large (max {MAX_INPUT_BYTES} bytes)")
    return bytes_to_image(data)


def optimize_bytes(
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
    """Optimize an image from raw bytes and return optimized bytes.

    Args:
        data: Raw image file bytes (JPEG, PNG, WEBP, etc.).
        max_width: Maximum width in pixels.
        max_height: Maximum height in pixels.
        quality: JPEG/WEBP quality (1-100).
        output_format: Target format as :class:`OutputFormat` or string.
        progressive: Use progressive JPEG encoding.
        optimize: Enable Pillow optimization flags.
        strip_metadata: Remove EXIF and other metadata.
        lossless: Use lossless compression for PNG/WEBP.
        auto_orient: Apply EXIF orientation before processing.
        fit: Resize fit mode: down, cover, contain, fill.
        anchor: Anchor point for cover/contain cropping.
        aspect_ratio: Target aspect ratio as '16:9' or (16, 9).
        background_color: RGB tuple or hex color for contain padding.

    Returns:
        A :class:`BytesResult` with the optimized image bytes and metadata.

    """
    if len(data) > MAX_INPUT_BYTES:
        return _bytes_error(
            f"Input too large (max {MAX_INPUT_BYTES} bytes)",
            original_size=len(data),
        )

    original_size = len(data)

    try:
        if isinstance(output_format, str):
            output_format = OutputFormat(output_format)
    except ValueError as exc:
        return _bytes_error(str(exc), original_size=original_size)

    try:
        if isinstance(fit, str) and fit:
            fit = FitMode(fit)
        if isinstance(anchor, str):
            anchor = Anchor(anchor)
    except ValueError as exc:
        return _bytes_error(str(exc), original_size=original_size)

    try:
        with Image.open(io.BytesIO(data)) as img:
            image: Image.Image = img
            image.load()
            if image.width > MAX_IMAGE_DIMENSION or image.height > MAX_IMAGE_DIMENSION:
                return _bytes_error(
                    f"Image dimensions too large: {image.width}x{image.height} "
                    f"(max {MAX_IMAGE_DIMENSION})",
                    original_size=original_size,
                )
            # Determine target format.
            source_fmt = image.format or "JPEG"
            if output_format in (OutputFormat.AUTO, OutputFormat.ORIGINAL):
                pillow_fmt = source_fmt
            else:
                pillow_fmt = FORMAT_MAP.get(output_format, "WEBP")

            is_animated = getattr(image, "is_animated", False) or getattr(image, "n_frames", 1) > 1

            if auto_orient and not is_animated:
                image = apply_exif_orientation(image)

            image = convert_mode(image, pillow_fmt)
            image = resize_image(
                image,
                max_width=max_width,
                max_height=max_height,
                fit=fit,
                anchor=anchor,
                aspect_ratio=aspect_ratio,
                background_color=background_color,
            )
            new_width, new_height = image.size

            try:
                optimized_data = image_to_bytes(
                    image,
                    fmt=pillow_fmt,
                    quality=quality,
                    progressive=progressive,
                    optimize=optimize,
                    strip_metadata=strip_metadata,
                    lossless=lossless,
                )
            finally:
                image.close()

            optimized_size = len(optimized_data)
            savings = original_size - optimized_size
            savings_pct = (savings / original_size * 100.0) if original_size > 0 else 0.0

            return BytesResult(
                data=optimized_data,
                format=pillow_fmt,
                width=new_width,
                height=new_height,
                original_size=original_size,
                optimized_size=optimized_size,
                savings_bytes=savings,
                savings_percent=savings_pct,
                success=True,
            )
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        _logger.error("Optimization failed", extra={"operation": "optimize_bytes"})
        return _bytes_error(str(exc), original_size=original_size)
    except (KeyboardInterrupt, SystemExit):
        raise


def optimize_base64(
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
    """Optimize an image from a base64 string and return base64 + metadata.

    Args:
        b64_str: Base64-encoded image data.

    Returns:
        A :class:`Base64Result` with base64 data and optimization metadata.

    """
    try:
        data = _b64.b64decode(b64_str)
    except (ValueError, TypeError) as exc:
        return Base64Result(
            base64=None,
            format="",
            width=0,
            height=0,
            original_size=0,
            optimized_size=0,
            savings_bytes=0,
            savings_percent=0.0,
            success=False,
            error=f"Invalid base64 data: {exc}",
        )

    result = optimize_bytes(
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

    return Base64Result(
        base64=_b64.b64encode(result.data).decode("ascii") if result.success else None,
        format=result.format,
        width=result.width,
        height=result.height,
        original_size=result.original_size,
        optimized_size=result.optimized_size,
        savings_bytes=result.savings_bytes,
        savings_percent=result.savings_percent,
        success=result.success,
        error=result.error,
    )


def _bytes_error(error: str, *, original_size: int = 0) -> BytesResult:
    """Create an error :class:`BytesResult`."""
    return BytesResult(
        data=b"",
        format="",
        width=0,
        height=0,
        original_size=original_size,
        optimized_size=0,
        savings_bytes=0,
        savings_percent=0.0,
        success=False,
        error=error,
    )
