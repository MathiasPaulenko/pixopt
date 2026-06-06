"""Generate responsive srcset images and HTML snippets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from optimg.models import OutputFormat
from optimg.optimizer import optimize_image


@dataclass(frozen=True)
class SrcsetImage:
    """A single responsive image variant."""

    width: int
    output_path: Path
    size_bytes: int


def _resolve_output_format(fmt_str: str) -> OutputFormat:
    fmt_upper = fmt_str.upper()
    for member in OutputFormat:
        if member.name == fmt_upper:
            return member
    return OutputFormat.WEBP


def generate_srcset_images(
    source: Path | str,
    output_dir: Path | str,
    widths: list[int],
    *,
    quality: int = 85,
    output_format: str = "WEBP",
    strip_metadata: bool = True,
    progressive: bool = True,
    optimize: bool = True,
    lossless: bool = False,
) -> list[SrcsetImage]:
    """Generate resized variants of an image for responsive srcset.

    Args:
        source: Path to the source image.
        output_dir: Directory where variants will be saved.
        widths: List of target widths in pixels. Each variant will have
            this width, preserving aspect ratio.
        quality: JPEG/WEBP quality (1-100).
        output_format: Pillow format string for output (e.g. "WEBP", "JPEG").
        strip_metadata: Remove EXIF and other metadata.
        progressive: Use progressive JPEG encoding.
        optimize: Enable Pillow optimizer.
        lossless: Use lossless compression for PNG/WEBP.

    Returns:
        List of SrcsetImage entries, sorted by width ascending.
    """
    source_path = Path(source)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fmt = _resolve_output_format(output_format)
    results: list[SrcsetImage] = []

    with Image.open(source_path) as img:
        img.load()
        orig_width = img.width
        ext = output_format.lower()
        if ext == "jpeg":
            ext = "jpg"

        for target_width in sorted(set(widths)):
            if target_width > orig_width:
                continue

            suffix = f"-{target_width}w.{ext}"
            out_path = out_dir / (source_path.stem + suffix)

            result = optimize_image(
                source_path,
                out_path,
                max_width=target_width,
                quality=quality,
                strip_metadata=strip_metadata,
                output_format=fmt,
                progressive=progressive,
                optimize=optimize,
                lossless=lossless,
            )

            if result.success:
                results.append(
                    SrcsetImage(
                        width=result.width,
                        output_path=out_path,
                        size_bytes=result.optimized_size,
                    )
                )

    return results
