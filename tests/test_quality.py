"""Tests for quality metrics (SSIM / PSNR)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli import app
from pixopt.quality import (
    QualityMetrics,
    compare_images,
    compute_mse,
    compute_psnr,
    compute_ssim,
)


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_image(
    output_dir: Path,
    name: str,
    size: tuple[int, int] = (100, 100),
    color: tuple[int, int, int] = (128, 128, 128),
) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, "PNG")
    return path


def _make_gradient(output_dir: Path, name: str, size: tuple[int, int] = (100, 100)) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size)
    pixels = img.load()
    assert pixels is not None
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = (x * 255 // size[0], y * 255 // size[1], 128)
    img.save(path, "PNG")
    return path


# ---------------------------------------------------------------------------
# compute_mse / compute_psnr tests
# ---------------------------------------------------------------------------


def test_compute_mse_identical() -> None:
    arr = np.zeros((10, 10, 3), dtype=np.float32)
    assert compute_mse(arr, arr) == 0.0


def test_compute_mse_different() -> None:
    a = np.zeros((10, 10, 3), dtype=np.float32)
    b = np.ones((10, 10, 3), dtype=np.float32) * 10
    mse = compute_mse(a, b)
    assert mse == 100.0


def test_compute_psnr_identical() -> None:
    assert compute_psnr(0.0) is None


def test_compute_psnr_value() -> None:
    psnr = compute_psnr(100.0)
    assert psnr is not None
    assert abs(psnr - 28.13) < 0.1  # 10*log10(255^2/100) ≈ 28.13


# ---------------------------------------------------------------------------
# compute_ssim tests
# ---------------------------------------------------------------------------


def test_compute_ssim_identical() -> None:
    arr = np.random.RandomState(42).randint(0, 256, (50, 50, 3)).astype(np.float32)
    ssim = compute_ssim(arr, arr)
    assert ssim == pytest.approx(1.0, abs=0.001)


def test_compute_ssim_different() -> None:
    arr1 = np.zeros((50, 50, 3), dtype=np.float32)
    arr2 = np.ones((50, 50, 3), dtype=np.float32) * 255
    ssim = compute_ssim(arr1, arr2)
    assert ssim < 0.1


def test_compute_ssim_shape_mismatch() -> None:
    a = np.zeros((50, 50, 3), dtype=np.float32)
    b = np.zeros((60, 60, 3), dtype=np.float32)
    with pytest.raises(ValueError, match="shapes"):
        compute_ssim(a, b)


# ---------------------------------------------------------------------------
# compare_images tests
# ---------------------------------------------------------------------------


def test_compare_images_identical(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "identical.png")
    result = compare_images(source, source)
    assert isinstance(result, QualityMetrics)
    assert result.ssim == pytest.approx(1.0, abs=0.001)
    assert result.psnr is None  # identical → infinite PSNR
    assert result.mse == pytest.approx(0.0, abs=0.01)
    assert result.verdict == "excellent"


def test_compare_images_different(output_dir: Path) -> None:
    orig = _make_gradient(output_dir, "orig.png")
    comp = _make_image(output_dir, "comp.png", color=(0, 0, 0))
    result = compare_images(orig, comp)
    assert result.ssim < 0.5
    assert result.psnr is not None
    assert result.psnr > 0
    assert result.mse > 0


def test_compare_images_slightly_different(output_dir: Path) -> None:
    orig = _make_gradient(output_dir, "sl_orig.png")
    # Create a slightly compressed version.
    comp_path = output_dir / "sl_comp.jpg"
    with Image.open(orig) as img:
        img.save(comp_path, "JPEG", quality=90)
    result = compare_images(orig, comp_path)
    assert result.ssim > 0.8  # should be high quality
    assert result.verdict in ("excellent", "good")


def test_compare_images_verdict_thresholds(output_dir: Path) -> None:
    orig = _make_gradient(output_dir, "verdict_orig.png")
    # Poor quality: heavy compression.
    comp_path = output_dir / "verdict_poor.jpg"
    with Image.open(orig) as img:
        img.save(comp_path, "JPEG", quality=5)
    result = compare_images(orig, comp_path)
    assert result.verdict in ("fair", "poor")


def test_compare_images_to_dict_serializable(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "dict.png")
    result = compare_images(source, source)
    d = result.to_dict()
    assert isinstance(d, dict)
    assert isinstance(d["original_path"], str)
    assert isinstance(d["compared_path"], str)
    assert "verdict" in d
    json.dumps(d)


def test_compare_images_file_not_found(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "fnf.png")
    with pytest.raises(FileNotFoundError):
        compare_images(source, "nonexistent.png")
    with pytest.raises(FileNotFoundError):
        compare_images("nonexistent.png", source)


def test_compare_images_dimension_mismatch(output_dir: Path) -> None:
    a = _make_image(output_dir, "dim_a.png", (100, 100))
    b = _make_image(output_dir, "dim_b.png", (200, 200))
    with pytest.raises(ValueError, match="dimensions"):
        compare_images(a, b)


def test_compare_images_input_too_large(output_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pixopt.image_ops.MAX_INPUT_BYTES", 10)
    a = _make_image(output_dir, "large_a.png", (10, 10))
    b = _make_image(output_dir, "large_b.png", (10, 10))
    a.write_bytes(b"\x00" * 11)
    b.write_bytes(b"\x00" * 11)
    with pytest.raises(ValueError, match="too large"):
        compare_images(a, b)


def test_compare_images_dimensions_in_result(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "dims.png", (150, 120))
    result = compare_images(source, source)
    assert result.width == 150
    assert result.height == 120


def test_compute_ssim_pixel_budget_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pixopt.quality.MAX_SSIM_PIXELS", 10)
    img1 = np.zeros((5, 5), dtype=np.float32)
    img2 = np.zeros((5, 5), dtype=np.float32)
    with pytest.raises(ValueError, match="pixel budget"):
        compute_ssim(img1, img2)


# ---------------------------------------------------------------------------
# CLI metrics command tests
# ---------------------------------------------------------------------------


def test_cli_metrics_basic(output_dir: Path) -> None:
    runner = CliRunner()
    orig = _make_gradient(output_dir, "cli_basic.png")
    comp_path = output_dir / "cli_basic_comp.jpg"
    with Image.open(orig) as img:
        img.save(comp_path, "JPEG", quality=80)
    result = runner.invoke(app, ["metrics", str(orig), str(comp_path)])
    assert result.exit_code == 0
    assert "SSIM" in result.output
    assert "PSNR" in result.output
    assert "MSE" in result.output
    assert "Verdict" in result.output


def test_cli_metrics_json_output(output_dir: Path) -> None:
    runner = CliRunner()
    orig = _make_gradient(output_dir, "cli_json.png")
    comp_path = output_dir / "cli_json_comp.jpg"
    with Image.open(orig) as img:
        img.save(comp_path, "JPEG", quality=80)
    result = runner.invoke(app, ["metrics", str(orig), str(comp_path), "--output", "json"])
    assert result.exit_code == 0
    assert '"ssim"' in result.output or "'ssim'" in result.output
    assert '"psnr"' in result.output or "'psnr'" in result.output


def test_cli_metrics_identical_images(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_gradient(output_dir, "cli_identical.png")
    result = runner.invoke(app, ["metrics", str(source), str(source)])
    assert result.exit_code == 0
    assert (
        "identical" in result.output.lower()
        or "infinity" in result.output.lower()
        or "\u221e" in result.output
    )


def test_cli_metrics_nonexistent_file(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_gradient(output_dir, "cli_nonexist.png")
    result = runner.invoke(app, ["metrics", str(source), "nonexistent.png"])
    assert result.exit_code != 0


def test_cli_metrics_dimension_mismatch(output_dir: Path) -> None:
    runner = CliRunner()
    a = _make_image(output_dir, "cli_mismatch_a.png", (100, 100))
    b = _make_image(output_dir, "cli_mismatch_b.png", (200, 200))
    result = runner.invoke(app, ["metrics", str(a), str(b)])
    assert result.exit_code != 0
