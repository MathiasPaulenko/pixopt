"""Color palette extraction from images.

Extracts *n* dominant colors from an image using a simple quantization
approach (Pillow's built-in quantize with median-cut, then sorted by
frequency).  Returns a list of :class:`ColorSwatch` dataclasses.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from pixopt.image_ops import _open_image

__all__ = ["ColorSwatch", "PaletteResult", "extract_palette"]

_DEFAULT_N = 6
_MAX_N = 32
_MIN_N = 1


@dataclass(frozen=True)
class ColorSwatch:
    """A single dominant color in the palette."""

    hex: str
    rgb: tuple[int, int, int]
    percent: float

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        d = asdict(self)
        d["rgb"] = list(d["rgb"])
        return d


@dataclass(frozen=True)
class PaletteResult:
    """Aggregated palette extraction result."""

    source_path: Path
    width: int
    height: int
    colors: list[ColorSwatch]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        return {
            "source_path": str(self.source_path),
            "width": self.width,
            "height": self.height,
            "colors": [c.to_dict() for c in self.colors],
        }


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert an RGB tuple to a hex string like ``#ff0080``."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def extract_palette(
    source: Path | str,
    n: int = _DEFAULT_N,
) -> PaletteResult:
    """Extract *n* dominant colors from an image.

    Uses Pillow's median-cut quantization to reduce the image to *n* colors,
    then counts pixel frequencies to rank them.

    Args:
        source: Path to the source image.
        n: Number of dominant colors to extract (1–32).

    Returns:
        A :class:`PaletteResult` with the extracted colors sorted by
        frequency (most dominant first).

    Raises:
        FileNotFoundError: If *source* does not exist.
        ValueError: If *n* is outside the valid range.
        PIL.UnidentifiedImageError: If the file is not a valid image.

    """
    if n < _MIN_N or n > _MAX_N:
        msg = f"n must be between {_MIN_N} and {_MAX_N}, got {n}"
        raise ValueError(msg)

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    with _open_image(path, label="source") as img:
        img.load()
        width, height = img.size

        # Convert to RGB for consistent processing.
        rgb_img = img.convert("RGB")

        # Quantize to n colors using median-cut.
        quantized = rgb_img.quantize(colors=n, method=Image.Quantize.MEDIANCUT)

        # Get the palette and pixel counts.
        palette = quantized.getpalette()
        if palette is None:
            return PaletteResult(
                source_path=path,
                width=width,
                height=height,
                colors=[],
            )

        # Count how many pixels map to each palette index.
        histogram = quantized.histogram()

        # Build (index, count) pairs, filter zero-count entries.
        counts = [(i, histogram[i]) for i in range(min(n, len(histogram))) if histogram[i] > 0]

        # Sort by count descending (most dominant first).
        counts.sort(key=lambda x: x[1], reverse=True)

        total_pixels = sum(c for _, c in counts) or 1

        swatches: list[ColorSwatch] = []
        for idx, count in counts:
            r = palette[idx * 3]
            g = palette[idx * 3 + 1]
            b = palette[idx * 3 + 2]
            rgb = (r, g, b)
            percent = (count / total_pixels) * 100
            swatches.append(
                ColorSwatch(
                    hex=_rgb_to_hex(rgb),
                    rgb=rgb,
                    percent=round(percent, 2),
                ),
            )

        return PaletteResult(
            source_path=path,
            width=width,
            height=height,
            colors=swatches,
        )
