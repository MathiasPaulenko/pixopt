"""Generate responsive srcset images and HTML snippets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pixopt._units import MAX_IMAGE_DIMENSION, MAX_SRCSET_WIDTHS
from pixopt.constants import FORMAT_MAP, FORMAT_TO_EXT
from pixopt.image_ops import _open_image
from pixopt.models import OutputFormat
from pixopt.optimizer import optimize_image
from pixopt.utils import validate_no_parent_references

__all__ = ["SrcsetImage", "generate_srcset_images"]


@dataclass(frozen=True)
class SrcsetImage:
    """A single responsive image variant."""

    width: int
    output_path: Path
    size_bytes: int


def _resolve_output_format(fmt_str: str) -> OutputFormat:
    fmt_upper = fmt_str.upper()
    for member in OutputFormat:
        if member.name == fmt_upper and member in FORMAT_MAP:
            return member
    valid = ", ".join(m.name for m in OutputFormat if m in FORMAT_MAP)
    raise ValueError(f"Unknown output format {fmt_str!r}. Valid formats: {valid}")


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
    if error := validate_no_parent_references(out_dir, "output_dir"):
        raise ValueError(error)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not widths:
        raise ValueError("widths must contain at least one positive value")

    if len(widths) > MAX_SRCSET_WIDTHS:
        raise ValueError(f"Too many srcset widths (max {MAX_SRCSET_WIDTHS})")

    for w in widths:
        if w < 1 or w > MAX_IMAGE_DIMENSION:
            raise ValueError(f"width must be between 1 and {MAX_IMAGE_DIMENSION}, got {w}")

    fmt = _resolve_output_format(output_format)
    results: list[SrcsetImage] = []

    pillow_fmt = FORMAT_MAP[fmt]
    ext = FORMAT_TO_EXT[pillow_fmt]

    with _open_image(source_path, label="source") as img:
        img.load()
        orig_width = img.width

        for target_width in sorted({w for w in widths if w > 0}):
            if target_width > orig_width:
                continue

            suffix = f"-{target_width}w{ext}"
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
                        output_path=result.output_path,
                        size_bytes=result.optimized_size,
                    ),
                )

    return results
