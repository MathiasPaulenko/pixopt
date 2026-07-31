"""Tests for PDF import/export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

pytest.importorskip("fitz")

from pixopt.cli.app import app
from pixopt.pdf_io import (
    PdfExportResult,
    PdfImportResult,
    PdfPageInfo,
    images_to_pdf,
    pdf_to_images,
)

runner = CliRunner()


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_image(
    output_dir: Path,
    name: str,
    size: tuple[int, int] = (200, 200),
    color: tuple[int, int, int] = (100, 150, 200),
    fmt: str = "PNG",
) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, fmt)
    return path


def _make_pdf(
    output_dir: Path, name: str, num_pages: int = 3, size: tuple[int, int] = (200, 300)
) -> Path:
    """Create a test PDF with the given number of pages using PyMuPDF."""
    import fitz

    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    for i in range(num_pages):
        page = doc.new_page(width=size[0], height=size[1])
        # Draw some content so pages aren't blank
        page.draw_rect(
            fitz.Rect(20, 20, size[0] - 20, size[1] - 20),
            color=(0.5, 0.3, 0.8),
            fill=(0.9, 0.8, 0.7),
        )
        page.insert_text((30, 50), f"Page {i + 1}", fontsize=24, color=(0, 0, 0))

    doc.save(path)
    doc.close()
    return path


# ---------------------------------------------------------------------------
# pdf_to_images tests
# ---------------------------------------------------------------------------


def test_pdf_to_images_basic(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "test.pdf", num_pages=3)
    out_dir = output_dir / "pages"
    result = pdf_to_images(pdf_path, out_dir)

    assert isinstance(result, PdfImportResult)
    assert result.success
    assert result.total_pages == 3
    assert len(result.pages) == 3

    for page in result.pages:
        assert isinstance(page, PdfPageInfo)
        assert page.width > 0
        assert page.height > 0
        assert page.output_path.exists()
        assert page.output_path.suffix == ".png"


def test_pdf_to_images_dpi(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "test.pdf", num_pages=1, size=(100, 100))
    out_low = output_dir / "low_dpi"
    out_high = output_dir / "high_dpi"

    result_low = pdf_to_images(pdf_path, out_low, dpi=72)
    result_high = pdf_to_images(pdf_path, out_high, dpi=300)

    assert result_low.success
    assert result_high.success
    assert result_high.pages[0].width > result_low.pages[0].width
    assert result_high.pages[0].height > result_low.pages[0].height


def test_pdf_to_images_format_jpeg(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "test.pdf", num_pages=2)
    out_dir = output_dir / "jpeg_pages"
    result = pdf_to_images(pdf_path, out_dir, fmt="JPEG")

    assert result.success
    for page in result.pages:
        assert page.output_path.suffix == ".jpeg"


def test_pdf_to_images_format_webp(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "test.pdf", num_pages=1)
    out_dir = output_dir / "webp_pages"
    result = pdf_to_images(pdf_path, out_dir, fmt="WEBP")

    assert result.success
    assert result.pages[0].output_path.suffix == ".webp"


def test_pdf_to_images_prefix(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "test.pdf", num_pages=2)
    out_dir = output_dir / "prefix_pages"
    result = pdf_to_images(pdf_path, out_dir, prefix="custom")

    assert result.success
    for page in result.pages:
        assert page.output_path.name.startswith("custom_")


def test_pdf_to_images_default_prefix(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "mydoc.pdf", num_pages=1)
    out_dir = output_dir / "default_prefix"
    result = pdf_to_images(pdf_path, out_dir)

    assert result.success
    assert result.pages[0].output_path.name.startswith("mydoc_")


def test_pdf_to_images_nonexistent_file(output_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        pdf_to_images(output_dir / "nonexistent.pdf", output_dir / "out")


def test_pdf_to_images_creates_output_dir(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "test.pdf", num_pages=1)
    out_dir = output_dir / "new_dir" / "sub"
    result = pdf_to_images(pdf_path, out_dir)

    assert result.success
    assert out_dir.exists()


def test_pdf_to_images_to_dict_serializable(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "test.pdf", num_pages=2)
    out_dir = output_dir / "dict_test"
    result = pdf_to_images(pdf_path, out_dir)

    d = result.to_dict()
    json.dumps(d)
    assert d["total_pages"] == 2
    assert d["success"] is True
    assert isinstance(d["pages"], list)


def test_pdf_to_images_single_page(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "single.pdf", num_pages=1)
    out_dir = output_dir / "single"
    result = pdf_to_images(pdf_path, out_dir)

    assert result.success
    assert result.total_pages == 1
    assert result.pages[0].page_number == 1


# ---------------------------------------------------------------------------
# images_to_pdf tests
# ---------------------------------------------------------------------------


def test_images_to_pdf_basic(output_dir: Path) -> None:
    img1 = _make_image(output_dir, "a.png", (200, 200), (255, 0, 0))
    img2 = _make_image(output_dir, "b.png", (300, 200), (0, 255, 0))
    out_pdf = output_dir / "output.pdf"

    result = images_to_pdf([img1, img2], out_pdf)

    assert isinstance(result, PdfExportResult)
    assert result.success
    assert result.page_count == 2
    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 0


def test_images_to_pdf_single_image(output_dir: Path) -> None:
    img = _make_image(output_dir, "single.png", (200, 200))
    out_pdf = output_dir / "single.pdf"

    result = images_to_pdf([img], out_pdf)

    assert result.success
    assert result.page_count == 1
    assert out_pdf.exists()


def test_images_to_pdf_empty_list_raises(output_dir: Path) -> None:
    with pytest.raises(ValueError, match="images list cannot be empty"):
        images_to_pdf([], output_dir / "empty.pdf")


def test_images_to_pdf_jpeg_images(output_dir: Path) -> None:
    img1 = _make_image(output_dir, "a.jpg", (200, 200), fmt="JPEG")
    img2 = _make_image(output_dir, "b.jpg", (300, 200), fmt="JPEG")
    out_pdf = output_dir / "from_jpeg.pdf"

    result = images_to_pdf([img1, img2], out_pdf)

    assert result.success
    assert result.page_count == 2


def test_images_to_pdf_rgba_conversion(output_dir: Path) -> None:
    img = Image.new("RGBA", (200, 200), (255, 0, 0, 128))
    img_path = output_dir / "rgba.png"
    img.save(img_path, "PNG")

    out_pdf = output_dir / "rgba.pdf"
    result = images_to_pdf([img_path], out_pdf)

    assert result.success
    assert out_pdf.exists()


def test_images_to_pdf_creates_parent_dir(output_dir: Path) -> None:
    img = _make_image(output_dir, "a.png")
    out_pdf = output_dir / "subdir" / "nested" / "output.pdf"

    result = images_to_pdf([img], out_pdf)

    assert result.success
    assert out_pdf.exists()


def test_images_to_pdf_with_title(output_dir: Path) -> None:
    img = _make_image(output_dir, "a.png")
    out_pdf = output_dir / "titled.pdf"

    result = images_to_pdf([img], out_pdf, title="My Document")

    assert result.success
    assert out_pdf.exists()


def test_images_to_pdf_to_dict_serializable(output_dir: Path) -> None:
    img = _make_image(output_dir, "a.png")
    out_pdf = output_dir / "dict.pdf"

    result = images_to_pdf([img], out_pdf)
    d = result.to_dict()
    json.dumps(d)
    assert d["page_count"] == 1
    assert d["success"] is True


def test_images_to_pdf_invalid_image(output_dir: Path) -> None:
    bad = output_dir / "bad.png"
    bad.write_bytes(b"not an image")
    out_pdf = output_dir / "bad.pdf"

    result = images_to_pdf([bad], out_pdf)

    assert not result.success
    assert result.error is not None


# ---------------------------------------------------------------------------
# Roundtrip: PDF → images → PDF
# ---------------------------------------------------------------------------


def test_pdf_roundtrip(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "original.pdf", num_pages=3)
    out_dir = output_dir / "roundtrip_images"
    result_import = pdf_to_images(pdf_path, out_dir, fmt="PNG")

    assert result_import.success
    image_paths = [p.output_path for p in result_import.pages]

    out_pdf = output_dir / "roundtrip.pdf"
    result_export = images_to_pdf(image_paths, out_pdf)

    assert result_export.success
    assert result_export.page_count == 3
    assert out_pdf.exists()


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_pdf_import_basic(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "cli_test.pdf", num_pages=2)
    out_dir = output_dir / "cli_pages"

    result = runner.invoke(app, ["pdf", str(pdf_path), "--output", str(out_dir)])

    assert result.exit_code == 0
    assert "2 pages" in result.output
    assert out_dir.exists()


def test_cli_pdf_import_json(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "cli_json.pdf", num_pages=2)
    out_dir = output_dir / "cli_json_pages"

    result = runner.invoke(app, ["pdf", str(pdf_path), "--output", str(out_dir), "--json"])

    assert result.exit_code == 0
    parsed = json.loads(result.stdout.strip())
    assert parsed["total_pages"] == 2
    assert parsed["success"] is True


def test_cli_pdf_import_dpi(output_dir: Path) -> None:
    pdf_path = _make_pdf(output_dir, "cli_dpi.pdf", num_pages=1, size=(100, 100))
    out_dir = output_dir / "cli_dpi_pages"

    result = runner.invoke(app, ["pdf", str(pdf_path), "--output", str(out_dir), "--dpi", "300"])

    assert result.exit_code == 0
    # At 300 DPI, a 100x100pt page should be ~417x417px
    with Image.open(out_dir / "cli_dpi_0001.png") as img:
        assert img.width > 300


def test_cli_pdf_export(output_dir: Path) -> None:
    img1 = _make_image(output_dir, "e1.png", (200, 200), (255, 0, 0))
    img2 = _make_image(output_dir, "e2.png", (200, 200), (0, 255, 0))
    out_pdf = output_dir / "cli_export.pdf"

    result = runner.invoke(
        app,
        ["pdf", str(out_pdf), "--from-images", str(img1), "--from-images", str(img2)],
    )

    assert result.exit_code == 0
    assert "PDF created" in result.output
    assert out_pdf.exists()


def test_cli_pdf_export_json(output_dir: Path) -> None:
    img = _make_image(output_dir, "ej.png")
    out_pdf = output_dir / "cli_export_json.pdf"

    result = runner.invoke(
        app,
        ["pdf", str(out_pdf), "--from-images", str(img), "--json"],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.stdout.strip())
    assert parsed["page_count"] == 1
    assert parsed["success"] is True


# ---------------------------------------------------------------------------
# Security / path traversal tests
# ---------------------------------------------------------------------------


def test_pdf_to_images_output_dir_parent_reference_rejected(
    output_dir: Path, tmp_path: Path
) -> None:
    pdf_path = _make_pdf(output_dir, "parent.pdf", num_pages=1)
    output_dir = tmp_path / "out" / ".."

    with pytest.raises(ValueError, match="parent"):
        pdf_to_images(pdf_path, output_dir)


def test_images_to_pdf_output_parent_reference_rejected(output_dir: Path, tmp_path: Path) -> None:
    img = _make_image(output_dir, "img.png")
    output = tmp_path / ".." / "out.pdf"

    with pytest.raises(ValueError, match="parent"):
        images_to_pdf([img], output)
