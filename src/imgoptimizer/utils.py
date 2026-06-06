"""Utility helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from imgoptimizer.constants import DEFAULT_EXTENSIONS


def discover_images(
    source_dir: Path,
    *,
    recursive: bool = False,
    extensions: Iterable[str] | None = None,
) -> Iterable[Path]:
    """Yield image file paths inside a directory."""
    exts = set(extensions or DEFAULT_EXTENSIONS)
    pattern = "**/*" if recursive else "*"
    for file_path in source_dir.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in exts:
            yield file_path
