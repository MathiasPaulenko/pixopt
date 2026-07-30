"""Low-level image manipulation operations."""

from __future__ import annotations

import contextlib
import warnings
from pathlib import Path
from typing import Any

import piexif  # type: ignore[import-untyped]
from PIL import Image
from PIL.Image import Resampling

from pixopt._units import WHITE
from pixopt.format_resolver import resolve_output_format
from pixopt.models import OutputFormat


def convert_mode(img: Image.Image, pillow_fmt: str) -> Image.Image:
    """Convert image mode so it can be saved in the requested format."""
    if pillow_fmt == "PNG":
        return img

    if pillow_fmt not in ("JPEG", "WEBP"):
        return img

    # JPEG and WEBP do not support alpha. Flatten any transparent image onto a
    # white background so the transparent areas are not replaced with an
    # unexpected color (Pillow's default is black when dropping alpha).
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, WHITE)
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img, mask=img.split()[1])
        return background

    if img.mode == "P" and "transparency" in img.info:
        rgb = img.convert("RGBA")
        background = Image.new("RGB", img.size, WHITE)
        background.paste(rgb, mask=rgb.split()[3])
        return background

    if img.mode == "RGB":
        return img

    return img.convert("RGB")


def resize_image(
    img: Image.Image,
    *,
    max_width: int | None = None,
    max_height: int | None = None,
    keep_aspect_ratio: bool = True,
) -> Image.Image:
    """Resize an image respecting optional bounds."""
    if not max_width and not max_height:
        return img

    if keep_aspect_ratio:
        img.thumbnail(
            (max_width or img.width, max_height or img.height),
            Resampling.LANCZOS,
        )
        return img

    target_width = max_width or img.width
    target_height = max_height or img.height
    return img.resize((target_width, target_height), Resampling.LANCZOS)


def build_save_kwargs(
    pillow_fmt: str,
    *,
    quality: int = 85,
    progressive: bool = True,
    optimize: bool = True,
    strip_metadata: bool = True,
    animated: bool = False,
    lossless: bool = False,
) -> dict[str, Any]:
    """Return Pillow-compatible save keyword arguments."""
    kwargs: dict[str, Any] = {"optimize": optimize}

    if pillow_fmt == "JPEG":
        kwargs["quality"] = quality
        kwargs["progressive"] = progressive
        if strip_metadata:
            kwargs["exif"] = b""
    elif pillow_fmt == "WEBP":
        kwargs["quality"] = quality
        kwargs["method"] = 6
        if lossless:
            kwargs["lossless"] = True
        if strip_metadata:
            kwargs["exif"] = b""
        if animated:
            kwargs["save_all"] = True
            kwargs["minimize"] = True
    elif pillow_fmt == "PNG":
        kwargs["compress_level"] = 9
    elif pillow_fmt == "GIF" and animated:
        kwargs["save_all"] = True
        kwargs["optimize"] = True

    return kwargs


def _pixel_data(img: Image.Image) -> list[Any]:
    """Return pixel data avoiding Pillow's deprecated getdata() when possible."""
    if hasattr(img, "get_flattened_data"):
        return list(img.get_flattened_data())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return list(img.getdata())


def strip_metadata_pillow(img: Image.Image, pillow_fmt: str) -> Image.Image:
    """Return a new image with all metadata removed (for non-JPEG/WEBP formats)."""
    if pillow_fmt in ("JPEG", "WEBP"):
        return img
    data = _pixel_data(img)
    clean = Image.new(img.mode, img.size)
    clean.putdata(data)
    if img.mode == "P":
        palette = img.getpalette()
        if palette is not None:
            clean.putpalette(palette)
    return clean


def strip_exif_post_process(path: Path, pillow_fmt: str) -> None:
    """Use piexif to aggressively strip remaining EXIF after Pillow save."""
    if pillow_fmt not in ("JPEG", "WEBP"):
        return
    with contextlib.suppress(Exception):
        piexif.remove(str(path))


def resolve_and_adjust_path(
    img: Image.Image,
    output_path: Path,
    output_format: OutputFormat,
) -> tuple[Path, str]:
    """Resolve format and ensure output path has the correct extension.

    Returns:
        Tuple of (adjusted_output_path, pillow_format_name).

    """
    ext, pillow_fmt = resolve_output_format(img, output_path, output_format)
    if output_path.suffix.lower() != ext:
        output_path = output_path.with_suffix(ext)
    return output_path, pillow_fmt
