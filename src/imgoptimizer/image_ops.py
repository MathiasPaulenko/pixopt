"""Low-level image manipulation operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import piexif
from PIL import Image
from PIL.Image import Resampling

from imgoptimizer.format_resolver import resolve_output_format
from imgoptimizer.models import OutputFormat


def convert_mode(img: Image.Image, pillow_fmt: str) -> Image.Image:
    """Convert image mode so it can be saved in the requested format."""
    original_mode = img.mode

    if pillow_fmt in ("JPEG", "WEBP") and original_mode in ("RGBA", "P", "LA", "L"):
        if original_mode == "P" and "transparency" in img.info:
            img = img.convert("RGBA")
        if original_mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if original_mode == "RGBA":
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img, mask=img.split()[1])
            return background
        return img.convert("RGB")

    if pillow_fmt == "PNG" and original_mode == "RGBA":
        return img

    if original_mode != "RGB" and pillow_fmt in ("JPEG", "WEBP"):
        return img.convert("RGB")

    return img


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


def strip_metadata_pillow(img: Image.Image, pillow_fmt: str) -> Image.Image:
    """Return a new image with all metadata removed (for non-JPEG/WEBP formats)."""
    if pillow_fmt in ("JPEG", "WEBP"):
        return img
    data = list(img.getdata())
    clean = Image.new(img.mode, img.size)
    clean.putdata(data)
    return clean


def strip_exif_post_process(path: Path, pillow_fmt: str) -> None:
    """Use piexif to aggressively strip remaining EXIF after Pillow save."""
    if pillow_fmt not in ("JPEG", "WEBP"):
        return
    try:
        piexif.remove(str(path))
    except Exception:
        pass


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
