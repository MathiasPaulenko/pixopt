"""Utility helpers."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pixopt.constants import DEFAULT_EXTENSIONS


def discover_images(
    source_dir: Path,
    *,
    recursive: bool = False,
    extensions: Iterable[str] | None = None,
) -> Iterable[Path]:
    """Yield image file paths inside a directory.

    Skips files that resolve outside of the source directory (e.g. symlink
    escapes or path-traversal attempts).
    """
    exts = set(extensions or DEFAULT_EXTENSIONS)
    base = source_dir.resolve()
    pattern = "**/*" if recursive else "*"
    for file_path in source_dir.glob(pattern):
        if not file_path.is_file():
            continue
        try:
            resolved = file_path.resolve()
        except (OSError, RuntimeError):
            # Broken or circular symlinks are skipped safely.
            continue
        if not resolved.is_relative_to(base):
            continue
        if file_path.suffix.lower() in exts:
            yield file_path
