"""Next-generation format support (JXL, WebP 2).

Provides detection and conversion infrastructure for next-gen image formats.
Support is gated on Pillow plugin availability — functions gracefully report
when a format is not yet supported by the installed ecosystem.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from PIL import Image

from pixopt.image_ops import _open_image
from pixopt.logging import get_logger
from pixopt.utils import validate_no_parent_references

__all__ = [
    "NextGenFormat",
    "FormatSupport",
    "FormatSupportInfo",
    "detect_format_support",
    "convert_to_nextgen",
    "is_format_supported",
]

_logger = get_logger("nextgen")


class NextGenFormat(str, Enum):
    """Next-generation image formats."""

    JXL = "jxl"
    WEBP2 = "webp2"


@dataclass
class FormatSupportInfo:
    """Support status for a single next-gen format."""

    format: str
    supported: bool
    plugin: str | None = None
    version: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "supported": self.supported,
            "plugin": self.plugin,
            "version": self.version,
            "note": self.note,
        }


@dataclass
class FormatSupport:
    """Aggregated support info for all next-gen formats."""

    formats: list[FormatSupportInfo]

    def to_dict(self) -> dict[str, Any]:
        return {"formats": [f.to_dict() for f in self.formats]}

    @property
    def any_supported(self) -> bool:
        return any(f.supported for f in self.formats)

    def get(self, fmt: str) -> FormatSupportInfo | None:
        for f in self.formats:
            if f.format == fmt:
                return f
        return None


def _check_jxl_support() -> FormatSupportInfo:
    """Check if JPEG XL (JXL) is available."""
    # Check for pillow-jxl-plugin
    try:
        import pillow_jxl  # type: ignore[import-not-found]  # noqa: F401

        return FormatSupportInfo(
            format="jxl",
            supported=True,
            plugin="pillow-jxl-plugin",
            version=getattr(pillow_jxl, "__version__", "unknown"),
        )
    except ImportError:
        pass

    # Check if Pillow natively supports JXL
    img = Image.new("RGB", (10, 10), (255, 0, 0))
    try:
        import io

        with io.BytesIO() as buf:
            img.save(buf, format="JXL")
        return FormatSupportInfo(
            format="jxl",
            supported=True,
            plugin="Pillow (native)",
        )
    except (ValueError, KeyError, OSError):
        pass
    finally:
        img.close()

    return FormatSupportInfo(
        format="jxl",
        supported=False,
        note="Install pillow-jxl-plugin for JXL support",
    )


def _check_webp2_support() -> FormatSupportInfo:
    """Check if WebP 2 is available."""
    img = Image.new("RGB", (10, 10), (255, 0, 0))
    try:
        import io

        with io.BytesIO() as buf:
            img.save(buf, format="WEBP2")
        return FormatSupportInfo(
            format="webp2",
            supported=True,
            plugin="Pillow (native)",
        )
    except (ValueError, KeyError, OSError):
        pass
    finally:
        img.close()

    return FormatSupportInfo(
        format="webp2",
        supported=False,
        note="WebP 2 is not yet supported by Pillow or its plugins",
    )


def detect_format_support() -> FormatSupport:
    """Detect which next-gen formats are available.

    Returns:
        A :class:`FormatSupport` with per-format support info.

    """
    formats = [
        _check_jxl_support(),
        _check_webp2_support(),
    ]

    support = FormatSupport(formats=formats)

    for f in formats:
        status = "supported" if f.supported else "not supported"
        _logger.debug(
            "Format detection: %s = %s",
            f.format,
            status,
            extra={"operation": "nextgen_detect", "format": f.format, "supported": f.supported},
        )

    return support


def is_format_supported(fmt: NextGenFormat | str) -> bool:
    """Check if a specific next-gen format is supported.

    Args:
        fmt: Format name (``"jxl"`` or ``"webp2"``).

    Returns:
        True if the format can be encoded by the current Pillow installation.

    """
    if isinstance(fmt, NextGenFormat):
        fmt = fmt.value

    support = detect_format_support()
    info = support.get(fmt)
    return info.supported if info else False


@dataclass
class ConversionResult:
    """Result of a next-gen format conversion."""

    source: Path
    output: Path
    format: str
    supported: bool
    success: bool
    original_size: int = 0
    output_size: int = 0
    savings_bytes: int = 0
    savings_percent: float = 0.0
    error: str | None = None
    fallback: bool = False
    fallback_format: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "output": str(self.output),
            "format": self.format,
            "supported": self.supported,
            "success": self.success,
            "original_size": self.original_size,
            "output_size": self.output_size,
            "savings_bytes": self.savings_bytes,
            "savings_percent": self.savings_percent,
            "error": self.error,
            "fallback": self.fallback,
            "fallback_format": self.fallback_format,
        }


def convert_to_nextgen(
    source: Path | str,
    output: Path | str,
    *,
    fmt: NextGenFormat | str = NextGenFormat.JXL,
    quality: int = 85,
    fallback: bool = True,
    fallback_format: str = "WEBP",
) -> ConversionResult:
    """Convert an image to a next-generation format.

    If the target format is not supported and ``fallback`` is True,
    converts to ``fallback_format`` instead.

    Args:
        source: Path to the source image.
        output: Output path. Extension will be adjusted if fallback occurs.
        fmt: Target next-gen format (``"jxl"`` or ``"webp2"``).
        quality: Quality for lossy compression (1-100).
        fallback: If True, fall back to ``fallback_format`` when the
            target format is not available.
        fallback_format: Format to use when falling back (default WEBP).

    Returns:
        A :class:`ConversionResult` with conversion details.

    Raises:
        FileNotFoundError: If the source image does not exist.
        ValueError: If the format is not supported and fallback is disabled.

    """
    if isinstance(fmt, NextGenFormat):
        fmt = fmt.value

    source_path = Path(source)
    if error := validate_no_parent_references(source_path, "source"):
        raise ValueError(error)
    try:
        original_size = source_path.stat().st_size
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Source file not found: {source_path}") from exc

    output_path = Path(output)
    if error := validate_no_parent_references(output_path, "output"):
        raise ValueError(error)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    supported = is_format_supported(fmt)

    if not supported:
        if not fallback:
            return ConversionResult(
                source=source_path,
                output=output_path,
                format=fmt,
                supported=False,
                success=False,
                original_size=original_size,
                error=f"Format '{fmt}' is not supported and fallback is disabled",
            )

        # Fall back to a supported format
        _logger.info(
            "Format %s not supported, falling back to %s",
            fmt,
            fallback_format,
            extra={"operation": "nextgen_convert", "format": fmt, "fallback": fallback_format},
        )

        pillow_fmt = fallback_format.upper()
        output_path = output_path.with_suffix(f".{fallback_format.lower()}")
    else:
        pillow_fmt = fmt.upper()

    try:
        image: Image.Image
        with _open_image(source_path, label="source") as img:
            img.load()
            image = img
            if image.mode != "RGB":
                image = image.convert("RGB")

            save_kwargs: dict[str, Any] = {}
            if pillow_fmt in ("JPEG", "WEBP", "JXL"):
                save_kwargs["quality"] = quality

            image.save(output_path, format=pillow_fmt, **save_kwargs)

        output_size = output_path.stat().st_size
        savings = original_size - output_size
        savings_pct = (savings / original_size * 100.0) if original_size > 0 else 0.0

        result = ConversionResult(
            source=source_path,
            output=output_path,
            format=fmt if supported else fallback_format,
            supported=supported,
            success=True,
            original_size=original_size,
            output_size=output_size,
            savings_bytes=savings,
            savings_percent=savings_pct,
            fallback=not supported,
            fallback_format=fallback_format if not supported else None,
        )

        _logger.info(
            "Conversion complete",
            extra={
                "operation": "nextgen_convert",
                "format": result.format,
                "fallback": result.fallback,
                "size_bytes": output_size,
            },
        )

        return result

    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        _logger.error(
            "Conversion failed",
            extra={"operation": "nextgen_convert", "format": fmt},
        )
        return ConversionResult(
            source=source_path,
            output=output_path,
            format=fmt,
            supported=supported,
            success=False,
            original_size=original_size,
            error=str(exc),
        )
