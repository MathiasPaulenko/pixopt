"""Tests for batch report and JSON CLI output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli import app
from pixopt.models import BatchReport
from pixopt.optimizer import batch_optimize


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_source(
    output_dir: Path, name: str, size: tuple[int, int] = (400, 300), quality: int = 95
) -> Path:
    path = output_dir / name
    img = Image.new("RGB", size)
    pixels = img.load()
    assert pixels is not None
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = (
                (x * 255) // size[0],
                (y * 255) // size[1],
                128,
            )
    img.save(path, "JPEG", quality=quality)
    return path


# ---------------------------------------------------------------------------
# batch_optimize unit tests
# ---------------------------------------------------------------------------


def test_batch_optimize_basic(output_dir: Path) -> None:
    s1 = _make_source(output_dir, "a.jpg")
    s2 = _make_source(output_dir, "b.jpg")
    out_dir = output_dir / "batch_out"

    report = batch_optimize([s1, s2], out_dir)
    assert isinstance(report, BatchReport)
    assert report.total_files == 2
    assert report.succeeded == 2
    assert report.failed == 0
    assert report.total_original_size > 0
    assert report.total_optimized_size > 0
    assert report.total_savings_bytes >= 0
    assert report.elapsed_seconds >= 0.0


def test_batch_optimize_savings_percent(output_dir: Path) -> None:
    s1 = _make_source(output_dir, "c.jpg", quality=95)
    out_dir = output_dir / "batch_savings"

    report = batch_optimize([s1], out_dir, quality=50)
    assert report.total_savings_percent > 0


def test_batch_optimize_creates_output_files(output_dir: Path) -> None:
    s1 = _make_source(output_dir, "d.jpg")
    s2 = _make_source(output_dir, "e.jpg")
    out_dir = output_dir / "batch_files"

    batch_optimize([s1, s2], out_dir)
    assert (out_dir / "d.jpg").exists()
    assert (out_dir / "e.jpg").exists()


def test_batch_optimize_to_dict_serializable(output_dir: Path) -> None:
    s1 = _make_source(output_dir, "f.jpg")
    out_dir = output_dir / "batch_dict"

    report = batch_optimize([s1], out_dir)
    d = report.to_dict()
    assert isinstance(d, dict)
    assert d["total_files"] == 1
    assert d["succeeded"] == 1
    assert isinstance(d["results"], list)
    json.dumps(d, default=str)


def test_batch_optimize_human_sizes(output_dir: Path) -> None:
    s1 = _make_source(output_dir, "g.jpg")
    out_dir = output_dir / "batch_human"

    report = batch_optimize([s1], out_dir)
    assert "B" in report.human_total_original or "KB" in report.human_total_original
    assert "B" in report.human_total_savings or "KB" in report.human_total_savings


def test_batch_optimize_with_failure(output_dir: Path) -> None:
    s1 = _make_source(output_dir, "h.jpg")
    bad = output_dir / "bad.jpg"
    bad.write_bytes(b"not an image")
    out_dir = output_dir / "batch_fail"

    report = batch_optimize([s1, bad], out_dir)
    assert report.total_files == 2
    assert report.succeeded == 1
    assert report.failed == 1


# ---------------------------------------------------------------------------
# CLI --output json tests
# ---------------------------------------------------------------------------


def test_cli_optimize_json_output(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir, "cli_opt.jpg")
    output = output_dir / "cli_opt_out.jpg"
    result = runner.invoke(
        app,
        ["optimize", str(source), str(output), "--output", "json"],
    )
    assert result.exit_code == 0
    assert '"success"' in result.output or "'success'" in result.output


def test_cli_convert_json_output(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir, "cli_conv.jpg")
    output = output_dir / "cli_conv_out.png"
    result = runner.invoke(
        app,
        ["convert", str(source), str(output), "--format", "png", "--output", "json"],
    )
    assert result.exit_code == 0
    assert '"success"' in result.output or "'success'" in result.output


def test_cli_batch_json_output(output_dir: Path) -> None:
    runner = CliRunner()
    s1 = _make_source(output_dir, "cli_b1.jpg")
    s2 = _make_source(output_dir, "cli_b2.jpg")
    out_dir = output_dir / "cli_batch_out"
    result = runner.invoke(
        app,
        ["batch", str(s1), str(s2), "--output-dir", str(out_dir), "--output", "json"],
    )
    assert result.exit_code == 0
    assert '"total_files"' in result.output or "'total_files'" in result.output
    assert '"succeeded"' in result.output or "'succeeded'" in result.output


def test_cli_batch_table_output(output_dir: Path) -> None:
    runner = CliRunner()
    s1 = _make_source(output_dir, "cli_bt1.jpg")
    s2 = _make_source(output_dir, "cli_bt2.jpg")
    out_dir = output_dir / "cli_batch_table"
    result = runner.invoke(
        app,
        ["batch", str(s1), str(s2), "--output-dir", str(out_dir)],
    )
    assert result.exit_code == 0
    assert "Batch Report" in result.output
    assert "succeeded" in result.output


def test_cli_optimize_table_output_default(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir, "cli_table.jpg")
    output = output_dir / "cli_table_out.jpg"
    result = runner.invoke(
        app,
        ["optimize", str(source), str(output)],
    )
    assert result.exit_code == 0
    assert "Optimized" in result.output
