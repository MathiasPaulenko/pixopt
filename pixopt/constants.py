"""Constants and lookup tables for image formats."""

from pixopt.models import OutputFormat

EXT_TO_FORMAT: dict[str, str] = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".avif": "AVIF",
    ".gif": "GIF",
    ".heic": "HEIF",
    ".heif": "HEIF",
}

FORMAT_TO_EXT: dict[str, str] = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "AVIF": ".avif",
    "GIF": ".gif",
    "HEIF": ".heic",
}

FORMAT_MAP: dict[OutputFormat, str] = {
    OutputFormat.JPEG: "JPEG",
    OutputFormat.PNG: "PNG",
    OutputFormat.WEBP: "WEBP",
    OutputFormat.AVIF: "AVIF",
}

DEFAULT_EXTENSIONS: set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff",
    ".gif",
    ".svg",
    ".heic",
    ".heif",
}

DEFAULT_FAVICON_SIZES: list[int] = [16, 32, 48, 64, 128, 256]
