"""Generate placeholders for lazy loading: dominant color, LQIP, blurhash."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Literal

from PIL import Image, ImageFilter


PlaceholderType = Literal["color", "lqip", "blurhash"]


def extract_dominant_color(img: Image.Image) -> str:
    """Return the dominant color of an image as a hex CSS string.

    Uses a downsample + average approach for accuracy.
    """
    rgb = img.convert("RGB")
    # Average all pixels by resizing to 1x1 with high-quality filter
    pixel = rgb.resize((1, 1), Image.Resampling.LANCZOS).getpixel((0, 0))
    return f"#{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}"


def generate_lqip_datauri(img: Image.Image, *, size: int = 32, quality: int = 20) -> str:
    """Generate a tiny blurred placeholder image as a base64 data URI.

    Args:
        img: Source PIL Image.
        size: Maximum dimension of the thumbnail (maintains aspect ratio).
        quality: JPEG quality for the tiny image (low = smaller).

    Returns:
        A base64 data URI string like 'data:image/jpeg;base64,/9j/4AAQ...'.
    """
    thumb = img.copy()
    thumb = thumb.convert("RGB")
    thumb.thumbnail((size, size), Image.Resampling.LANCZOS)
    thumb = thumb.filter(ImageFilter.GaussianBlur(radius=2))

    buf = io.BytesIO()
    thumb.save(buf, format="JPEG", quality=quality, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _encode_base83(value: int, length: int) -> str:
    """Encode an integer into a base-83 string of fixed length."""
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%*+,-.:;=?@[]^_{|}~"
    result = []
    for _ in range(length):
        result.append(alphabet[value % 83])
        value //= 83
    return "".join(reversed(result))


def generate_blurhash(img: Image.Image, *, components_x: int = 4, components_y: int = 3) -> str:
    """Generate a simplified blurhash-like string from an image.

    This is a pure-Python approximation that encodes average colors of a
    grid into a compact base-83 string. It is NOT the official BlurHash
    algorithm, but produces visually similar short placeholders.

    Args:
        img: Source PIL Image.
        components_x: Number of horizontal grid cells.
        components_y: Number of vertical grid cells.

    Returns:
        A short blurhash-like string.
    """
    rgb = img.convert("RGB")
    w, h = rgb.size
    cell_w = max(1, w // components_x)
    cell_h = max(1, h // components_y)

    # Size flag (components - 1) each fits in one char
    size_flag = (components_y - 1) * 9 + (components_x - 1)
    parts: list[str] = [_encode_base83(size_flag, 1)]

    for cy in range(components_y):
        for cx in range(components_x):
            x1 = cx * cell_w
            y1 = cy * cell_h
            x2 = min(w, x1 + cell_w)
            y2 = min(h, y1 + cell_h)
            region = rgb.crop((x1, y1, x2, y2))
            data = region.tobytes()
            n = len(data) // 3
            if n == 0:
                r = g = b = 0
            else:
                r = sum(data[i] for i in range(0, len(data), 3)) // n
                g = sum(data[i + 1] for i in range(0, len(data), 3)) // n
                b = sum(data[i + 2] for i in range(0, len(data), 3)) // n
            # Pack RGB into a single base83 value
            packed = (r << 16) | (g << 8) | b
            parts.append(_encode_base83(packed, 4))

    return "".join(parts)


def generate_placeholder(
    image_path: Path,
    *,
    placeholder_type: PlaceholderType = "lqip",
    lqip_size: int = 32,
    lqip_quality: int = 20,
) -> str:
    """Generate a placeholder string for an image.

    Args:
        image_path: Path to the source image.
        placeholder_type: One of 'color', 'lqip', 'blurhash'.
        lqip_size: Max thumbnail dimension for LQIP.
        lqip_quality: JPEG quality for LQIP.

    Returns:
        A CSS color string, base64 data URI, or blurhash string.
    """
    with Image.open(image_path) as img:
        img.load()
        if placeholder_type == "color":
            return extract_dominant_color(img)
        if placeholder_type == "lqip":
            return generate_lqip_datauri(img, size=lqip_size, quality=lqip_quality)
        if placeholder_type == "blurhash":
            return generate_blurhash(img)
    return ""
