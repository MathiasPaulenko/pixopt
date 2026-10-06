"""Directory inventory / scan.

Scan a directory and return a structured list of image info plus
aggregate statistics.  Useful for audits and the MCP answering
"what do I have?".
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from pixopt._units import MAX_INPUT_BYTES, MAX_SCAN_ENTRIES
from pixopt.constants import DEFAULT_EXTENSIONS
from pixopt.image_ops import _open_image
from pixopt.logging import get_logger
from pixopt.utils import discover_images, validate_no_parent_references

__all__ = ["ScanEntry", "ScanReport", "scan_directory"]

_logger = get_logger("inventory")


@dataclass
class ScanEntry:
    """Information about a single image file found during a scan."""

    file_path: Path
    file_size: int
    width: int
    height: int
    format: str
    mode: str
    has_alpha: bool
    is_animated: bool
    frame_count: int
    error: str | None = None

    @property
    def human_file_size(self) -> str:
        """Human-readable file size."""
        from pixopt.models import _human_readable_size

        return _human_readable_size(self.file_size)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "file_size": self.file_size,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "mode": self.mode,
            "has_alpha": self.has_alpha,
            "is_animated": self.is_animated,
            "frame_count": self.frame_count,
            "error": self.error,
        }


@dataclass
class ScanReport:
    """Aggregate statistics for a directory scan."""

    directory: Path
    total_files: int
    valid_images: int
    errors: int
    total_size_bytes: int
    entries: list[ScanEntry] = field(default_factory=list)
    formats: dict[str, int] = field(default_factory=dict)
    largest_file: Path | None = None
    largest_size: int = 0
    smallest_file: Path | None = None
    smallest_size: int = 0

    @property
    def human_total_size(self) -> str:
        """Human-readable total size."""
        from pixopt.models import _human_readable_size

        return _human_readable_size(self.total_size_bytes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directory": str(self.directory),
            "total_files": self.total_files,
            "valid_images": self.valid_images,
            "errors": self.errors,
            "total_size_bytes": self.total_size_bytes,
            "entries": [e.to_dict() for e in self.entries],
            "formats": dict(self.formats),
            "largest_file": str(self.largest_file) if self.largest_file else None,
            "largest_size": self.largest_size,
            "smallest_file": str(self.smallest_file) if self.smallest_file else None,
            "smallest_size": self.smallest_size,
        }


def scan_directory(
    directory: Path | str,
    *,
    recursive: bool = False,
    extensions: Iterable[str] | None = None,
) -> ScanReport:
    """Scan a directory and return structured image info plus aggregate stats.

    Args:
        directory: Directory to scan.
        recursive: If True, scan subdirectories recursively.
        extensions: Optional list of file extensions to include (e.g. ``[".jpg", ".png"]``).
            Defaults to the built-in set of supported image extensions.

    Returns:
        A :class:`ScanReport` with per-file entries and aggregate statistics.

    Raises:
        FileNotFoundError: If the directory does not exist.

    """
    dir_path = Path(directory)
    if error := validate_no_parent_references(dir_path, "directory"):
        raise ValueError(error)
    try:
        dir_path.stat()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Directory not found: {dir_path}") from exc

    _logger.debug("Scanning directory", extra={"operation": "scan", "path": str(dir_path)})

    exts = set(extensions) if extensions is not None else set(DEFAULT_EXTENSIONS)

    entries: list[ScanEntry] = []
    total_size = 0
    formats: dict[str, int] = {}
    largest_file: Path | None = None
    largest_size = 0
    smallest_file: Path | None = None
    smallest_size = MAX_INPUT_BYTES + 1
    error_count = 0
    valid_count = 0

    for file_path in discover_images(dir_path, recursive=recursive, extensions=exts):
        if len(entries) >= MAX_SCAN_ENTRIES:
            _logger.warning(
                "Scan stopped after reaching the entry limit",
                extra={"operation": "scan", "limit": MAX_SCAN_ENTRIES},
            )
            break

        try:
            file_size = file_path.stat().st_size
        except OSError:
            # File vanished between discovery and stat.
            continue

        try:
            with _open_image(file_path, label="source") as img:
                img.load()
                fmt = img.format or "UNKNOWN"
                mode = img.mode
                width = img.width
                height = img.height
                has_alpha = "A" in mode or "transparency" in img.info
                is_animated = getattr(img, "is_animated", False)
                frame_count = getattr(img, "n_frames", 1)

            entry = ScanEntry(
                file_path=file_path,
                file_size=file_size,
                width=width,
                height=height,
                format=fmt,
                mode=mode,
                has_alpha=has_alpha,
                is_animated=is_animated,
                frame_count=frame_count,
            )
            valid_count += 1
            total_size += file_size
            formats[fmt] = formats.get(fmt, 0) + 1

            if largest_file is None or file_size > largest_size:
                largest_file = file_path
                largest_size = file_size
            if smallest_file is None or file_size < smallest_size:
                smallest_file = file_path
                smallest_size = file_size

        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            entry = ScanEntry(
                file_path=file_path,
                file_size=file_size,
                width=0,
                height=0,
                format="UNKNOWN",
                mode="",
                has_alpha=False,
                is_animated=False,
                frame_count=0,
                error=str(exc),
            )
            error_count += 1

        entries.append(entry)

    if smallest_file is None:
        smallest_size = 0

    report = ScanReport(
        directory=dir_path,
        total_files=len(entries),
        valid_images=valid_count,
        errors=error_count,
        total_size_bytes=total_size,
        entries=entries,
        formats=formats,
        largest_file=largest_file,
        largest_size=largest_size,
        smallest_file=smallest_file,
        smallest_size=smallest_size,
    )

    _logger.info(
        "Scan complete",
        extra={"operation": "scan", "path": str(dir_path), "size_bytes": valid_count},
    )

    return report
