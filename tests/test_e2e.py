"""End-to-end tests that invoke the real CLI as a subprocess."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image


def _run(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    sep = os.pathsep
    env["PYTHONPATH"] = f"{root}{sep}{current}" if current else str(root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "pixopt.cli", *args],
        text=True,
        capture_output=True,
        check=check,
        env=env,
    )


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    src = tmp_path / "photo.jpg"
    Image.new("RGB", (800, 600), color=(255, 0, 0)).save(src, quality=95)
    return src


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    d = tmp_path / "images"
    d.mkdir()
    Image.new("RGB", (200, 200)).save(d / "a.jpg")
    Image.new("RGB", (200, 200)).save(d / "b.png")
    return d


def test_e2e_help() -> None:
    result = _run("--help")
    assert result.returncode == 0
    assert "Optimize images" in result.stdout


def test_e2e_optimize_file(sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.jpg"
    result = _run("optimize", str(sample_image), str(out), "--quality", "50")
    assert result.returncode == 0, result.stderr
    assert out.exists()


def test_e2e_optimize_directory(sample_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "optimized"
    result = _run("optimize", str(sample_dir), str(out), "--recursive")
    assert result.returncode == 0, result.stderr
    assert (out / "a.jpg").exists()
    assert (out / "b.png").exists()


def test_e2e_convert_format(sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.webp"
    result = _run("convert", str(sample_image), str(out), "-f", "webp")
    assert result.returncode == 0, result.stderr
    assert out.exists()
    assert out.suffix == ".webp"


def test_e2e_favicon(sample_image: Path, tmp_path: Path) -> None:
    src = tmp_path / "logo.png"
    Image.new("RGBA", (256, 256), color=(255, 0, 0, 128)).save(src)
    out = tmp_path / "favicon.ico"
    result = _run("favicon", str(src), str(out))
    assert result.returncode == 0, result.stderr
    assert out.exists()


def test_e2e_info(sample_image: Path) -> None:
    result = _run("info", str(sample_image))
    assert result.returncode == 0, result.stderr
    assert "800x600" in result.stdout


def test_e2e_placeholder(sample_image: Path) -> None:
    result = _run("placeholder", str(sample_image), "--type", "color")
    assert result.returncode == 0, result.stderr
    assert "#" in result.stdout


def test_e2e_srcset(sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "responsive"
    html = tmp_path / "snippet.html"
    result = _run(
        "srcset",
        str(sample_image),
        "--sizes",
        "200,400",
        "--output-dir",
        str(out),
        "--html",
        str(html),
    )
    assert result.returncode == 0, result.stderr
    assert html.exists()


def test_e2e_compare(sample_image: Path, tmp_path: Path) -> None:
    html = tmp_path / "compare.html"
    result = _run("compare", str(sample_image), str(html), "--quality", "50")
    assert result.returncode == 0, result.stderr
    assert html.exists()


def test_e2e_batch(sample_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "batch"
    result = _run(
        "batch",
        str(sample_dir / "a.jpg"),
        str(sample_dir / "b.png"),
        "-o",
        str(out),
        "--quality",
        "50",
    )
    assert result.returncode == 0, result.stderr
    assert (out / "a.jpg").exists()
    assert (out / "b.png").exists()


def test_e2e_invalid_command() -> None:
    result = _run("not-a-command")
    assert result.returncode != 0
