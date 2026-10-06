"""PDF import/export.

Convert PDF pages to images and images to PDF.
Useful for document workflows.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from pixopt._units import (
    MAX_IMAGE_DIMENSION,
    MAX_PDF_DPI,
    MAX_PDF_IMAGES,
    MAX_PDF_PAGES,
    MAX_PDF_SIZE_BYTES,
    MAX_PDF_TOTAL_PIXELS,
)
from pixopt.image_ops import _open_image
from pixopt.logging import get_logger
from pixopt.utils import validate_no_parent_references

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - optional dependency
    try:
        import fitz
    except ImportError:
        fitz = None

__all__ = [
    "PdfPageInfo",
    "PdfImportResult",
    "PdfExportResult",
    "pdf_to_images",
    "images_to_pdf",
]

_logger = get_logger("pdf_io")


@dataclass
class PdfPageInfo:
    """Information about a single extracted PDF page."""

    page_number: int
    width: int
    height: int
    output_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "output_path": str(self.output_path),
        }


@dataclass
class PdfImportResult:
    """Result of converting a PDF to images."""

    source: Path
    pages: list[PdfPageInfo] = field(default_factory=list)
    total_pages: int = 0
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "total_pages": self.total_pages,
            "pages": [p.to_dict() for p in self.pages],
            "success": self.success,
            "error": self.error,
        }


@dataclass
class PdfExportResult:
    """Result of converting images to a PDF."""

    output: Path
    page_count: int = 0
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": str(self.output),
            "page_count": self.page_count,
            "success": self.success,
            "error": self.error,
        }


def pdf_to_images(
    source: Path | str,
    output_dir: Path | str,
    *,
    dpi: int = 150,
    fmt: str = "PNG",
    prefix: str | None = None,
) -> PdfImportResult:
    """Convert each page of a PDF to an image file.

    Args:
        source: Path to the PDF file.
        output_dir: Directory where page images will be saved.
        dpi: Render resolution in DPI (default 150).
        fmt: Output image format (``"PNG"``, ``"JPEG"``, ``"WEBP"``).
        prefix: Filename prefix. Defaults to the PDF stem.

    Returns:
        A :class:`PdfImportResult` with per-page info.

    Raises:
        FileNotFoundError: If the PDF does not exist.

    """
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"PDF file not found: {source_path}")

    if fitz is None:
        return PdfImportResult(
            source=source_path,
            success=False,
            error="PDF support requires PyMuPDF. Install it with: pip install pixopt[pdf]",
        )

    if source_path.stat().st_size > MAX_PDF_SIZE_BYTES:
        return PdfImportResult(
            source=source_path,
            success=False,
            error=f"PDF file exceeds maximum size of {MAX_PDF_SIZE_BYTES} bytes",
        )

    if dpi < 1 or dpi > MAX_PDF_DPI:
        return PdfImportResult(
            source=source_path,
            success=False,
            error=f"dpi must be between 1 and {MAX_PDF_DPI}, got {dpi}",
        )

    out_dir = Path(output_dir)
    if error := validate_no_parent_references(out_dir, "output_dir"):
        raise ValueError(error)
    out_dir.mkdir(parents=True, exist_ok=True)

    name_prefix = prefix or source_path.stem
    pillow_fmt = fmt.upper()

    _logger.debug(
        "Converting PDF to images", extra={"operation": "pdf_import", "path": str(source_path)}
    )

    doc: Any | None = None
    try:
        doc = fitz.open(source_path)

        if len(doc) > MAX_PDF_PAGES:
            return PdfImportResult(
                source=source_path,
                success=False,
                error=f"PDF has too many pages (max {MAX_PDF_PAGES})",
            )
        pages: list[PdfPageInfo] = []

        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        total_pixels = 0
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=matrix)
            if pix.width > MAX_IMAGE_DIMENSION or pix.height > MAX_IMAGE_DIMENSION:
                return PdfImportResult(
                    source=source_path,
                    success=False,
                    error=f"PDF page dimensions too large: {pix.width}x{pix.height} "
                    f"(max {MAX_IMAGE_DIMENSION})",
                )
            total_pixels += pix.width * pix.height
            if total_pixels > MAX_PDF_TOTAL_PIXELS:
                return PdfImportResult(
                    source=source_path,
                    success=False,
                    error="PDF total pixel budget exceeded: "
                    f"{total_pixels} (max {MAX_PDF_TOTAL_PIXELS})",
                )
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            out_path = out_dir / f"{name_prefix}_{page_num + 1:04d}.{pillow_fmt.lower()}"
            img.save(out_path, pillow_fmt)
            img.close()

            pages.append(
                PdfPageInfo(
                    page_number=page_num + 1,
                    width=pix.width,
                    height=pix.height,
                    output_path=out_path,
                )
            )

        result = PdfImportResult(
            source=source_path,
            pages=pages,
            total_pages=len(pages),
            success=True,
        )

        _logger.info(
            "PDF import complete",
            extra={"operation": "pdf_import", "path": str(source_path), "size_bytes": len(pages)},
        )

        return result

    except (OSError, ValueError, RuntimeError) as exc:
        _logger.error(
            "PDF import failed", extra={"operation": "pdf_import", "path": str(source_path)}
        )
        return PdfImportResult(
            source=source_path,
            total_pages=0,
            success=False,
            error=str(exc),
        )
    finally:
        if doc is not None:
            doc.close()


def images_to_pdf(
    images: Sequence[Path | str],
    output: Path | str,
    *,
    title: str | None = None,
) -> PdfExportResult:
    """Combine multiple images into a single PDF file.

    Args:
        images: List of image file paths. Each image becomes one page.
        output: Output PDF file path.
        title: Optional PDF document title metadata.

    Returns:
        A :class:`PdfExportResult` with the output path and page count.

    Raises:
        ValueError: If the image list is empty.

    """
    if not images:
        raise ValueError("images list cannot be empty")

    output_path = Path(output)
    if error := validate_no_parent_references(output_path, "output"):
        raise ValueError(error)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _logger.debug(
        "Converting images to PDF", extra={"operation": "pdf_export", "path": str(output_path)}
    )

    if len(images) > MAX_PDF_IMAGES:
        raise ValueError(f"Too many images for PDF (max {MAX_PDF_IMAGES}), got {len(images)}")

    pil_images: list[Image.Image] = []
    try:
        total_pixels = 0
        for img_path in images:
            image: Image.Image
            with _open_image(Path(img_path), label="source") as img:
                image = img
            if image.mode != "RGB":
                image = image.convert("RGB")
            total_pixels += image.width * image.height
            if total_pixels > MAX_PDF_TOTAL_PIXELS:
                raise ValueError(
                    f"PDF total pixel budget exceeded: {total_pixels} (max {MAX_PDF_TOTAL_PIXELS})"
                )
            pil_images.append(image)

        save_kwargs: dict[str, Any] = {}
        if title:
            save_kwargs["title"] = title

        pil_images[0].save(
            output_path,
            format="PDF",
            save_all=True,
            append_images=pil_images[1:],
            **save_kwargs,
        )

        result = PdfExportResult(
            output=output_path,
            page_count=len(pil_images),
            success=True,
        )

        _logger.info(
            "PDF export complete",
            extra={
                "operation": "pdf_export",
                "path": str(output_path),
                "size_bytes": len(pil_images),
            },
        )

        return result

    except (OSError, ValueError, RuntimeError) as exc:
        _logger.error(
            "PDF export failed", extra={"operation": "pdf_export", "path": str(output_path)}
        )
        return PdfExportResult(
            output=output_path,
            page_count=0,
            success=False,
            error=str(exc),
        )
    finally:
        for img in pil_images:
            img.close()
