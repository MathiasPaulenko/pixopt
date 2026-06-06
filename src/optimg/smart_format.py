"""Smart format detection to recommend the most efficient output format."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from optimg.models import OutputFormat


def has_transparency(img: Image.Image) -> bool:
    """Check if the image contains any transparent or semi-transparent pixels."""
    mode = img.mode
    if mode in ("RGBA", "LA"):
        alpha = img.split()[-1]
        data = alpha.tobytes()
        return any(b < 255 for b in data)
    if mode == "P":
        # Check if palette has transparency
        if "transparency" in img.info:
            return True
        # Convert to RGBA and check
        rgba = img.convert("RGBA")
        alpha = rgba.split()[-1]
        data = alpha.tobytes()
        return any(b < 255 for b in data)
    return False


def count_unique_colors(img: Image.Image, max_colors: int = 1024) -> int:
    """Count unique colors in the image, capped at max_colors.

    Uses a histogram approach with reduced precision for performance.
    """
    rgb = img.convert("RGB")
    small = rgb.resize((100, 100), Image.Resampling.LANCZOS)
    data = small.tobytes()
    colors: set[tuple[int, int, int]] = set()
    for i in range(0, len(data), 3):
        colors.add((data[i], data[i + 1], data[i + 2]))
        if len(colors) >= max_colors:
            return max_colors
    return len(colors)


def is_photo(img: Image.Image) -> bool:
    """Heuristic: returns True if the image looks like a photograph.

    Photos tend to have many unique colors and smooth gradients.
    Graphics/UI tend to have fewer colors and sharp edges.
    """
    unique = count_unique_colors(img, max_colors=512)
    return unique >= 300


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

    with Image.open(path) as img:
        img.load()

        is_animated = (
            getattr(img, "is_animated", False)
            or getattr(img, "n_frames", 1) > 1
        )
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
