"""Smart format detection to recommend the most efficient output format."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from pixopt._units import (
    COLOR_SAMPLE_SIZE,
    MAX_CHANNEL_VALUE,
    MAX_IMAGE_DIMENSION,
    MAX_UNIQUE_COLORS,
    SMART_FORMAT_PHOTO_THRESHOLD,
)
from pixopt.image_ops import _open_image
from pixopt.models import OutputFormat

__all__ = [
    "count_unique_colors",
    "detect_optimal_format",
    "has_transparency",
    "is_photo",
]


def has_transparency(img: Image.Image) -> bool:
    """Check if the image contains any transparent or semi-transparent pixels."""
    mode = img.mode
    if mode in ("RGBA", "LA"):
        alpha = img.split()[-1]
        data = alpha.tobytes()
        return any(b < MAX_CHANNEL_VALUE for b in data)
    if mode == "P":
        # Check if palette has transparency
        if "transparency" in img.info:
            return True
        # Convert to RGBA and check
        rgba = img.convert("RGBA")
        try:
            alpha = rgba.split()[-1]
            data = alpha.tobytes()
            return any(b < MAX_CHANNEL_VALUE for b in data)
        finally:
            rgba.close()
    return False


def count_unique_colors(img: Image.Image, max_colors: int = MAX_UNIQUE_COLORS) -> int:
    """Count unique colors in the image, capped at max_colors.

    Uses a histogram approach with reduced precision for performance.
    """
    rgb = img.convert("RGB")
    small: Image.Image | None = None
    try:
        small = rgb.resize((COLOR_SAMPLE_SIZE, COLOR_SAMPLE_SIZE), Image.Resampling.LANCZOS)
        data = small.tobytes()
        colors: set[tuple[int, int, int]] = set()
        for i in range(0, len(data), 3):
            colors.add((data[i], data[i + 1], data[i + 2]))
            if len(colors) >= max_colors:
                return max_colors
        return len(colors)
    finally:
        if small is not None:
            small.close()
        rgb.close()


def is_photo(img: Image.Image) -> bool:
    """Heuristic: returns True if the image looks like a photograph.

    Photos tend to have many unique colors and smooth gradients.
    Graphics/UI tend to have fewer colors and sharp edges.
    """
    unique = count_unique_colors(img, max_colors=512)
    return unique >= SMART_FORMAT_PHOTO_THRESHOLD


def detect_optimal_format(
    image_path: Path | str,
    *,
    allow_lossy: bool = True,
    allow_lossless: bool = True,
    allow_animation: bool = True,
) -> OutputFormat:
    """Analyze an image and return the most efficient output format.

    Rules:
        - Transparent image → WEBP (or PNG if lossless only)
        - Animated image → WEBP
        - Photograph with many colors → WEBP (or JPEG if no WEBP)
        - Graphic/UI with few colors → WEBP lossless or PNG
    """
    path = Path(image_path)

    try:
        with _open_image(path, label="source") as img:
            img.load()
            if img.width > MAX_IMAGE_DIMENSION or img.height > MAX_IMAGE_DIMENSION:
                return OutputFormat.WEBP

            is_animated = getattr(img, "is_animated", False) or getattr(img, "n_frames", 1) > 1
            if is_animated and allow_animation:
                return OutputFormat.WEBP

            transparent = has_transparency(img)
            photo = is_photo(img)

            if transparent:
                if allow_lossless:
                    return OutputFormat.WEBP
                return OutputFormat.PNG

            if photo and allow_lossy:
                return OutputFormat.WEBP

            if not photo and allow_lossless:
                return OutputFormat.WEBP

            if allow_lossy:
                return OutputFormat.JPEG

            return OutputFormat.PNG
    except (UnidentifiedImageError, Image.DecompressionBombError, ValueError):
        # Corrupt, too large or otherwise unreadable images fall back to a
        # widely supported default so the caller can report a controlled error
        # through optimize_image instead of crashing.
        return OutputFormat.WEBP
