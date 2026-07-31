"""Tests for format benchmark feature."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.benchmark import BenchmarkResult, BenchmarkVariant, benchmark_formats
from pixopt.cli import app


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_source(
    output_dir: Path,
    name: str = "source.jpg",
    size: tuple[int, int] = (800, 600),
    quality: int = 95,
) -> Path:
    """Create a test image with enough detail to produce different sizes."""
    path = output_dir / name
    # Create a gradient image with some noise for realistic compression behavior.
    img = Image.new("RGB", size)
    pixels = img.load()
    assert pixels is not None
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = (
                (x * 255) // size[0],
                (y * 255) // size[1],
                ((x + y) * 255) // (size[0] + size[1]),
            )
    img.save(path, "JPEG", quality=quality)
    return path


# ---------------------------------------------------------------------------
# benchmark_formats unit tests
# ---------------------------------------------------------------------------


def test_benchmark_returns_result(output_dir: Path) -> None:
    source = _make_source(output_dir)
    result = benchmark_formats(source)
    assert isinstance(result, BenchmarkResult)
    assert result.source_format == "JPEG"
    assert result.width == 800
    assert result.height == 600
    assert len(result.variants) > 0


def test_benchmark_variants_have_sizes(output_dir: Path) -> None:
    source = _make_source(output_dir)
    result = benchmark_formats(source)
    for v in result.variants:
        assert v.size_bytes > 0
        assert isinstance(v, BenchmarkVariant)


def test_benchmark_recommends_smallest(output_dir: Path) -> None:
    source = _make_source(output_dir)
    result = benchmark_formats(source)
    assert result.recommended_format != ""
    assert result.recommended_size > 0
    # The recommended variant should be the smallest.
    smallest = min(result.variants, key=lambda v: v.size_bytes)
    assert result.recommended_size == smallest.size_bytes
    assert result.recommended_format == smallest.format
    assert result.recommended_quality == smallest.quality


def test_benchmark_savings_percent(output_dir: Path) -> None:
    source = _make_source(output_dir)
    result = benchmark_formats(source)
    for v in result.variants:
        expected = (1 - v.size_bytes / result.source_size) * 100
        assert abs(v.savings_percent - round(expected, 2)) < 0.1


def test_benchmark_custom_qualities(output_dir: Path) -> None:
    source = _make_source(output_dir)
    result = benchmark_formats(source, qualities=[80, 90])
    # Should have variants for each format at q80 and q90, plus PNG.
    jpeg_variants = [v for v in result.variants if v.format == "JPEG"]
    assert len(jpeg_variants) == 2
    assert {v.quality for v in jpeg_variants} == {80, 90}


def test_benchmark_custom_formats(output_dir: Path) -> None:
    source = _make_source(output_dir)
    result = benchmark_formats(source, formats=["JPEG", "PNG"])
    fmts = {v.format for v in result.variants}
    assert fmts == {"JPEG", "PNG"}


def test_benchmark_to_dict_serializable(output_dir: Path) -> None:
    source = _make_source(output_dir)
    result = benchmark_formats(source)
    d = result.to_dict()
    assert isinstance(d, dict)
    assert isinstance(d["source_path"], str)
    json.dumps(d, default=str)


def test_benchmark_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        benchmark_formats("nonexistent.jpg")


def test_benchmark_corrupt_file(output_dir: Path) -> None:
    path = output_dir / "corrupt.jpg"
    path.write_bytes(b"not an image")
    from PIL import UnidentifiedImageError

    with pytest.raises(UnidentifiedImageError):
        benchmark_formats(path)


def test_benchmark_human_sizes(output_dir: Path) -> None:
    source = _make_source(output_dir)
    result = benchmark_formats(source)
    assert "B" in result.human_source_size or "KB" in result.human_source_size
    assert "B" in result.human_recommended_size or "KB" in result.human_recommended_size


def test_benchmark_variant_label() -> None:
    v1 = BenchmarkVariant(format="JPEG", quality=80, size_bytes=1000, savings_percent=50.0)
    assert v1.label == "JPEG@q80"
    v2 = BenchmarkVariant(format="PNG", quality=None, size_bytes=2000, savings_percent=30.0)
    assert v2.label == "PNG"


# ---------------------------------------------------------------------------
# CLI benchmark command tests
# ---------------------------------------------------------------------------


def test_cli_benchmark_basic(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    result = runner.invoke(app, ["benchmark", str(source)])
    assert result.exit_code == 0
    assert "JPEG" in result.output
    assert "Recommended" in result.output


def test_cli_benchmark_json_output(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    result = runner.invoke(app, ["benchmark", str(source), "--json"])
    assert result.exit_code == 0
    assert '"variants"' in result.output or "'variants'" in result.output


def test_cli_benchmark_custom_qualities(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    result = runner.invoke(
        app,
        ["benchmark", str(source), "-q", "80", "-q", "90"],
    )
    assert result.exit_code == 0
    assert "q80" in result.output
    assert "q90" in result.output


def test_cli_benchmark_custom_formats(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    result = runner.invoke(
        app,
        ["benchmark", str(source), "-f", "JPEG", "-f", "PNG"],
    )
    assert result.exit_code == 0
    assert "JPEG" in result.output
    assert "PNG" in result.output


def test_cli_benchmark_nonexistent_file() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["benchmark", "nonexistent.jpg"])
    assert result.exit_code != 0
