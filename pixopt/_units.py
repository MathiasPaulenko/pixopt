"""Unit and pixel constants shared across the package."""

from __future__ import annotations

__all__ = [
    "BYTES_PER_KB",
    "BYTES_PER_MB",
    "COLOR_SAMPLE_SIZE",
    "MAX_CHANNEL_VALUE",
    "MAX_QUALITY",
    "MAX_UNIQUE_COLORS",
    "MIN_QUALITY",
    "PERCENT",
    "SMART_FORMAT_PHOTO_THRESHOLD",
    "WHITE",
]

# Byte unit conversion
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024

# Max value for an 8-bit channel
MAX_CHANNEL_VALUE = 255

# Common colors
WHITE: tuple[int, int, int] = (MAX_CHANNEL_VALUE, MAX_CHANNEL_VALUE, MAX_CHANNEL_VALUE)

# Quality / percentage
MIN_QUALITY = 1
MAX_QUALITY = 100
PERCENT = 100

# Smart format detection
COLOR_SAMPLE_SIZE = 100
MAX_UNIQUE_COLORS = 1024
SMART_FORMAT_PHOTO_THRESHOLD = 300
