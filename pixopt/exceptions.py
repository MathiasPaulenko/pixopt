"""Typed exception hierarchy for pixopt.

Replaces broad ``except Exception`` with specific exceptions so that
library consumers can catch precise error conditions.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "PixoptError",
    "ImageNotFoundError",
    "UnsupportedFormatError",
    "OptimizationError",
    "ConversionError",
    "ResizeError",
    "WatermarkError",
    "EXIFError",
    "PipelineError",
    "BundleError",
    "InvalidParameterError",
]


class PixoptError(Exception):
    """Base exception for all pixopt errors."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.path = Path(path) if path is not None else None

    def __str__(self) -> str:
        if self.path is not None:
            return f"{self.message}: {self.path}"
        return self.message


class ImageNotFoundError(PixoptError, FileNotFoundError):
    """Raised when a source image file does not exist."""

    def __init__(self, path: Path | str) -> None:
        super().__init__(f"File not found: {path}", path=path)


class UnsupportedFormatError(PixoptError):
    """Raised when an image format is not supported."""

    def __init__(self, fmt: str, *, path: Path | str | None = None) -> None:
        super().__init__(f"Unsupported format: {fmt!r}", path=path)
        self.fmt = fmt


class OptimizationError(PixoptError):
    """Raised when image optimization fails."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        super().__init__(message, path=path)


class ConversionError(PixoptError):
    """Raised when image format conversion fails."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        super().__init__(message, path=path)


class ResizeError(PixoptError):
    """Raised when image resizing fails."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        super().__init__(message, path=path)


class WatermarkError(PixoptError):
    """Raised when watermark application fails."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        super().__init__(message, path=path)


class EXIFError(PixoptError):
    """Raised when EXIF reading or writing fails."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        super().__init__(message, path=path)


class PipelineError(PixoptError):
    """Raised when a pipeline operation fails."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        super().__init__(message, path=path)


class BundleError(PixoptError):
    """Raised when asset bundle generation fails."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        super().__init__(message, path=path)


class InvalidParameterError(PixoptError):
    """Raised when an invalid parameter is passed to a function."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        super().__init__(message, path=path)
