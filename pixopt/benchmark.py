"""Format benchmark: generate variants and recommend the best format.

Produces variants in JPEG / WEBP / AVIF / PNG at several quality levels,
measures file size, and recommends the smallest variant that meets a
quality threshold.
"""

from __future__ import annotations

import io
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from pixopt._units import BYTES_PER_KB
from pixopt.image_ops import _open_image, convert_mode
from pixopt.utils import validate_no_parent_references

__all__ = ["BenchmarkResult", "BenchmarkVariant", "benchmark_formats"]

# Formats and quality levels to test.
_BENCHMARK_FORMATS: list[tuple[str, list[int | None]]] = [
    ("JPEG", [50, 60, 70, 80, 90, None]),
    ("WEBP", [50, 60, 70, 80, 90, None]),
    ("AVIF", [50, 60, 70, 80, 90, None]),
    ("PNG", [None]),  # PNG is lossless; no quality parameter.
]

# AVIF requires pillow-avif-plugin or pillow-heif.  Check at runtime.
_AVIF_AVAILABLE: bool | None = None


def _check_avif() -> bool:
    """Check whether AVIF encoding is available."""
    global _AVIF_AVAILABLE
    if _AVIF_AVAILABLE is None:
        try:
            with io.BytesIO() as buf:
                img = Image.new("RGB", (4, 4))
                img.save(buf, "AVIF")
                img.close()
                _AVIF_AVAILABLE = True
        except (OSError, ValueError, Image.DecompressionBombError, KeyError):
            _AVIF_AVAILABLE = False
    return _AVIF_AVAILABLE


@dataclass(frozen=True)
class BenchmarkVariant:
    """A single variant produced during benchmarking."""

    format: str
    quality: int | None
    size_bytes: int
    savings_percent: float

    @property
    def label(self) -> str:
        """Human-readable label for this variant."""
        if self.quality is not None:
            return f"{self.format}@q{self.quality}"
        return self.format


@dataclass(frozen=True)
class BenchmarkResult:
    """Aggregated benchmark result with a recommendation."""

    source_path: Path
    source_size: int
    source_format: str
    width: int
    height: int
    variants: list[BenchmarkVariant] = field(default_factory=list)
    recommended_format: str = ""
    recommended_quality: int | None = None
    recommended_size: int = 0
    recommended_savings: float = 0.0

    @property
    def human_source_size(self) -> str:
        """Return the source file size as a human-readable string."""
        return _human_size(self.source_size)

    @property
    def human_recommended_size(self) -> str:
        """Return the recommended variant size as a human-readable string."""
        return _human_size(self.recommended_size)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        d = asdict(self)
        d["source_path"] = str(d["source_path"])
        return d


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human readable string."""
    if size_bytes < BYTES_PER_KB:
        return f"{size_bytes} B"
    return f"{size_bytes / BYTES_PER_KB:.2f} KB"


def _encode_variant(
    img: Image.Image,
    fmt: str,
    quality: int | None,
) -> int:
    """Encode *img* as *fmt* with *quality* and return the byte size.

    Returns 0 if encoding fails.
    """
    converted: Image.Image | None = None
    try:
        converted = convert_mode(img, fmt)
        with io.BytesIO() as buf:
            save_kwargs: dict[str, Any] = {}
            if quality is not None:
                save_kwargs["quality"] = quality
            if fmt in ("JPEG", "WEBP"):
                save_kwargs["optimize"] = True
            if fmt == "JPEG":
                save_kwargs["progressive"] = True
            converted.save(buf, format=fmt, **save_kwargs)
            return buf.tell()
    except (OSError, ValueError, Image.DecompressionBombError, KeyError):
        return 0
    finally:
        if converted is not None and converted is not img:
            converted.close()


def benchmark_formats(
    source: Path | str,
    *,
    qualities: list[int] | None = None,
    formats: list[str] | None = None,
) -> BenchmarkResult:
    """Benchmark an image across formats and quality levels.

    Args:
        source: Path to the source image.
        qualities: Custom quality levels to test. Defaults to [50, 60, 70, 80, 90].
        formats: Custom list of formats to test. Defaults to JPEG, WEBP, AVIF, PNG.

    Returns:
        A :class:`BenchmarkResult` with all variants and a recommendation.

    Raises:
        FileNotFoundError: If *source* does not exist.
        PIL.UnidentifiedImageError: If the file is not a valid image.

    """
    path = Path(source)
    if error := validate_no_parent_references(path, "source"):
        raise ValueError(error)
    try:
        source_size = path.stat().st_size
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Image file not found: {path}") from exc

    with _open_image(path, label="source") as img:
        img.load()
        source_format = img.format or "UNKNOWN"
        width, height = img.size

        # Build the format/quality matrix.
        q_levels = qualities if qualities is not None else [50, 60, 70, 80, 90]
        fmt_list = (
            [f.upper() for f in formats]
            if formats is not None
            else [
                "JPEG",
                "WEBP",
                "AVIF",
                "PNG",
            ]
        )

        # Filter out AVIF if not available.
        if "AVIF" in fmt_list and not _check_avif():
            fmt_list = [f for f in fmt_list if f != "AVIF"]

        variants: list[BenchmarkVariant] = []

        for fmt in fmt_list:
            if fmt == "PNG":
                # PNG is lossless — single variant.
                size = _encode_variant(img, "PNG", None)
                if size > 0:
                    savings = (1 - size / source_size) * 100 if source_size > 0 else 0.0
                    variants.append(
                        BenchmarkVariant(
                            format="PNG",
                            quality=None,
                            size_bytes=size,
                            savings_percent=round(savings, 2),
                        ),
                    )
            else:
                for q in q_levels:
                    size = _encode_variant(img, fmt, q)
                    if size > 0:
                        savings = (1 - size / source_size) * 100 if source_size > 0 else 0.0
                        variants.append(
                            BenchmarkVariant(
                                format=fmt,
                                quality=q,
                                size_bytes=size,
                                savings_percent=round(savings, 2),
                            ),
                        )

        # Recommendation: smallest variant (most savings).
        # Prefer lossy formats over PNG for web use, but PNG wins if it's smaller.
        recommended: BenchmarkVariant | None = None
        if variants:
            recommended = min(variants, key=lambda v: v.size_bytes)

        return BenchmarkResult(
            source_path=path,
            source_size=source_size,
            source_format=source_format,
            width=width,
            height=height,
            variants=variants,
            recommended_format=recommended.format if recommended else "",
            recommended_quality=recommended.quality if recommended else None,
            recommended_size=recommended.size_bytes if recommended else 0,
            recommended_savings=recommended.savings_percent if recommended else 0.0,
        )
