"""Watermark and overlay utilities.

Provides functions to add text or image watermarks onto a base image with
configurable position, opacity, padding, and scaling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from pixopt._units import MAX_IMAGE_DIMENSION
from pixopt.image_ops import _open_image
from pixopt.utils import validate_no_parent_references

__all__ = [
    "WatermarkPosition",
    "WatermarkResult",
    "add_image_watermark",
    "add_text_watermark",
]


class WatermarkPosition(str, Enum):
    """Position of the watermark on the base image."""

    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    CENTER = "center"


# Default font size for text watermarks.
_DEFAULT_FONT_SIZE = 36
# Default opacity (0–255 for alpha).
_DEFAULT_OPACITY = 128
# Maximum allowed watermark text length (prevents DoS from huge strings).
_MAX_TEXT_LENGTH = 1000


@dataclass(frozen=True)
class WatermarkResult:
    """Result of a watermark operation."""

    source_path: Path
    output_path: Path
    width: int
    height: int
    watermark_type: str  # "text" or "image"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        d = asdict(self)
        d["source_path"] = str(d["source_path"])
        d["output_path"] = str(d["output_path"])
        return d


def _resolve_position(
    base_size: tuple[int, int],
    overlay_size: tuple[int, int],
    position: WatermarkPosition,
    padding: int,
) -> tuple[int, int]:
    """Calculate the (x, y) paste coordinates for the overlay."""
    bw, bh = base_size
    ow, oh = overlay_size

    if position == WatermarkPosition.TOP_LEFT:
        return padding, padding
    if position == WatermarkPosition.TOP_RIGHT:
        return bw - ow - padding, padding
    if position == WatermarkPosition.BOTTOM_LEFT:
        return padding, bh - oh - padding
    if position == WatermarkPosition.BOTTOM_RIGHT:
        return bw - ow - padding, bh - oh - padding
    # center
    return (bw - ow) // 2, (bh - oh) // 2


def _apply_opacity(img: Image.Image, opacity: float) -> Image.Image:
    """Apply opacity (0.0–1.0) to an RGBA image."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda px: int(px * opacity))
    return Image.merge("RGBA", (r, g, b, a))


def add_text_watermark(
    source: Path | str,
    output: Path | str,
    text: str,
    *,
    position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT,
    opacity: float = 0.5,
    padding: int = 20,
    font_size: int = _DEFAULT_FONT_SIZE,
    font_path: Path | str | None = None,
    color: tuple[int, int, int] = (255, 255, 255),
) -> WatermarkResult:
    """Add a text watermark to an image.

    Args:
        source: Path to the source image.
        output: Path for the output image.
        text: Watermark text.
        position: Where to place the watermark.
        opacity: Opacity from 0.0 (transparent) to 1.0 (opaque).
        padding: Pixel padding from the edge.
        font_size: Font size in pixels.
        font_path: Optional path to a TTF/OTF font file.
        color: Text color as (R, G, B).

    Returns:
        A :class:`WatermarkResult`.
    """
    if padding < 0 or padding > MAX_IMAGE_DIMENSION:
        raise ValueError(f"padding must be between 0 and {MAX_IMAGE_DIMENSION}, got {padding}")
    if font_size < 1 or font_size > 1000:
        raise ValueError(f"font_size must be between 1 and 1000, got {font_size}")
    if not isinstance(text, str):
        raise ValueError(f"text must be a string, got {type(text).__name__}")
    if len(text) > _MAX_TEXT_LENGTH:
        raise ValueError(f"text exceeds maximum length of {_MAX_TEXT_LENGTH} characters")

    src_path = Path(source)
    out_path = Path(output)
    if error := validate_no_parent_references(out_path, "output"):
        raise ValueError(error)

    with _open_image(src_path, label="source") as _base:
        _base.load()
        base = _base.convert("RGBA")
        bw, bh = base.size

        if bw > MAX_IMAGE_DIMENSION or bh > MAX_IMAGE_DIMENSION:
            msg = (
                f"Image dimensions too large: {bw}x{bh} "
                f"(max {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION})"
            )
            raise ValueError(msg)

        # Create transparent overlay for text.
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        try:
            draw = ImageDraw.Draw(overlay)

            # Load font.
            font: ImageFont.ImageFont | ImageFont.FreeTypeFont
            if font_path:
                font_path_obj = Path(font_path)
                if error := validate_no_parent_references(font_path_obj, "font_path"):
                    raise ValueError(error)
                if font_path_obj.suffix.lower() not in {".ttf", ".otf"}:
                    raise ValueError("font_path must be a .ttf or .otf file")
                try:
                    stat = font_path_obj.stat()
                except FileNotFoundError as exc:
                    raise FileNotFoundError(f"Font file not found: {font_path_obj}") from exc
                if stat.st_size > 10 * 1024 * 1024:
                    raise ValueError("font file too large (max 10 MB)")
                font = ImageFont.truetype(str(font_path), font_size)
            else:
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except OSError:
                    font = ImageFont.load_default()

            # Measure text size.
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = int(bbox[2] - bbox[0])
            th = int(bbox[3] - bbox[1])

            x, y = _resolve_position((bw, bh), (tw, th), position, padding)

            # Draw text with opacity.
            alpha = int(255 * max(0.0, min(1.0, opacity)))
            draw.text((x, y), text, fill=(color[0], color[1], color[2], alpha), font=font)

            # Composite.
            result = Image.alpha_composite(base, overlay)
            result = result.convert("RGB")

            out_path.parent.mkdir(parents=True, exist_ok=True)
            result.save(out_path)
            result.close()
        finally:
            overlay.close()
            base.close()

    return WatermarkResult(
        source_path=src_path,
        output_path=out_path,
        width=bw,
        height=bh,
        watermark_type="text",
    )


def add_image_watermark(
    source: Path | str,
    output: Path | str,
    watermark: Path | str,
    *,
    position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT,
    opacity: float = 0.5,
    padding: int = 20,
    scale: float | None = None,
) -> WatermarkResult:
    """Add an image watermark (logo/overlay) onto a base image.

    Args:
        source: Path to the source image.
        output: Path for the output image.
        watermark: Path to the watermark image (PNG with alpha recommended).
        position: Where to place the watermark.
        opacity: Opacity from 0.0 (transparent) to 1.0 (opaque).
        padding: Pixel padding from the edge.
        scale: Scale factor for the watermark relative to the base image width.
            If None, the watermark is used at its original size.

    Returns:
        A :class:`WatermarkResult`.
    """
    if padding < 0 or padding > MAX_IMAGE_DIMENSION:
        raise ValueError(f"padding must be between 0 and {MAX_IMAGE_DIMENSION}, got {padding}")
    if scale is not None and (scale <= 0 or scale > 10):
        raise ValueError(f"scale must be between 0 and 10, got {scale}")

    src_path = Path(source)
    wm_path = Path(watermark)
    out_path = Path(output)
    if error := validate_no_parent_references(out_path, "output"):
        raise ValueError(error)
    if error := validate_no_parent_references(wm_path, "watermark"):
        raise ValueError(error)

    with _open_image(src_path, label="source") as _base:
        _base.load()
        base = _base.convert("RGBA")
        wm: Image.Image | None = None
        try:
            bw, bh = base.size

            if bw > MAX_IMAGE_DIMENSION or bh > MAX_IMAGE_DIMENSION:
                msg = (
                    f"Image dimensions too large: {bw}x{bh} "
                    f"(max {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION})"
                )
                raise ValueError(msg)

            with _open_image(wm_path, label="watermark") as _wm:
                _wm.load()
                wm = _wm.convert("RGBA")

                if scale is not None:
                    if wm.width <= 0 or wm.height <= 0:
                        raise ValueError(
                            f"Watermark image has invalid dimensions: {wm.width}x{wm.height}"
                        )
                    new_w = int(bw * scale)
                    new_h = int(wm.height * (new_w / wm.width))
                    resized = wm.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    wm.close()
                    wm = resized

                opacity = max(0.0, min(1.0, opacity))
                original_wm = wm
                wm = _apply_opacity(wm, opacity)
                original_wm.close()

                x, y = _resolve_position(base.size, wm.size, position, padding)

                # Composite watermark onto base.
                base.paste(wm, (x, y), wm)
                result = base.convert("RGB")

                out_path.parent.mkdir(parents=True, exist_ok=True)
                result.save(out_path)
                result.close()
        finally:
            if wm is not None:
                wm.close()
            base.close()

    return WatermarkResult(
        source_path=src_path,
        output_path=out_path,
        width=bw,
        height=bh,
        watermark_type="image",
    )
