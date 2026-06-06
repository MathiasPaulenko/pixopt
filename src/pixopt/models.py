"""Domain models and enums."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class OutputFormat(str, Enum):
    """Supported output formats."""

    AUTO = "auto"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    AVIF = "avif"
    ORIGINAL = "original"


@dataclass(frozen=True)
class OptimizationResult:
    """Result of an image optimization operation."""

    source_path: Path
    output_path: Path
    original_size: int
    optimized_size: int
    savings_bytes: int
    savings_percent: float
    width: int
    height: int
    format: str
    metadata_removed: bool
    success: bool
    error: str | None = None

    @property
    def human_original_size(self) -> str:
        return _human_readable_size(self.original_size)

    @property
    def human_optimized_size(self) -> str:
        return _human_readable_size(self.optimized_size)

    @property
    def human_savings(self) -> str:
        return _human_readable_size(self.savings_bytes)


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"
