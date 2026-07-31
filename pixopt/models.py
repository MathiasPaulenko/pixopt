"""Domain models and enums."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from pixopt._units import BYTES_PER_KB, BYTES_PER_MB

__all__ = ["Anchor", "BatchReport", "FitMode", "ImageInfo", "OptimizationResult", "OutputFormat"]


class OutputFormat(str, Enum):
    """Supported output formats."""

    AUTO = "auto"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    AVIF = "avif"
    ORIGINAL = "original"


class FitMode(str, Enum):
    """How an image should be resized within the target dimensions."""

    DOWN = "down"
    COVER = "cover"
    CONTAIN = "contain"
    FILL = "fill"


class Anchor(str, Enum):
    """Anchor point used when cropping or positioning an image."""

    CENTER = "center"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    FACE = "face"


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
        """Return the original size as a human-readable string."""
        return _human_readable_size(self.original_size)

    @property
    def human_optimized_size(self) -> str:
        """Return the optimized size as a human-readable string."""
        return _human_readable_size(self.optimized_size)

    @property
    def human_savings(self) -> str:
        """Return the saved bytes as a human-readable string."""
        return _human_readable_size(self.savings_bytes)


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human readable string."""
    if size_bytes < BYTES_PER_KB:
        return f"{size_bytes} B"
    if size_bytes < BYTES_PER_MB:
        return f"{size_bytes / BYTES_PER_KB:.2f} KB"
    return f"{size_bytes / BYTES_PER_MB:.2f} MB"


@dataclass(frozen=True)
class ImageInfo:
    """Structured metadata for an image file."""

    file_path: Path
    file_size: int
    width: int
    height: int
    mode: str
    format: str
    dpi: tuple[float, float] | None = None
    has_alpha: bool = False
    is_animated: bool = False
    frame_count: int = 1
    exif: dict[str, object] = field(default_factory=dict)
    icc_profile: bool = False
    orientation: int | None = None

    @property
    def human_file_size(self) -> str:
        """Return the file size as a human-readable string."""
        return _human_readable_size(self.file_size)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict representation."""
        d = asdict(self)
        d["file_path"] = str(d["file_path"])
        return d


@dataclass(frozen=True)
class BatchReport:
    """Aggregated report for a batch optimization run."""

    results: list[OptimizationResult]
    total_files: int
    succeeded: int
    failed: int
    total_original_size: int
    total_optimized_size: int
    total_savings_bytes: int
    total_savings_percent: float
    elapsed_seconds: float

    @property
    def human_total_original(self) -> str:
        """Return the total original size as a human-readable string."""
        return _human_readable_size(self.total_original_size)

    @property
    def human_total_optimized(self) -> str:
        """Return the total optimized size as a human-readable string."""
        return _human_readable_size(self.total_optimized_size)

    @property
    def human_total_savings(self) -> str:
        """Return the total savings as a human-readable string."""
        return _human_readable_size(self.total_savings_bytes)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict representation."""
        return {
            "total_files": self.total_files,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "total_original_size": self.total_original_size,
            "total_optimized_size": self.total_optimized_size,
            "total_savings_bytes": self.total_savings_bytes,
            "total_savings_percent": round(self.total_savings_percent, 2),
            "elapsed_seconds": round(self.elapsed_seconds, 4),
            "results": [
                r.__dict__ | {"source_path": str(r.source_path), "output_path": str(r.output_path)}
                for r in self.results
            ],
        }
