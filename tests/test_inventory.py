"""Tests for directory inventory / scan."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli.app import app
from pixopt.inventory import ScanEntry, ScanReport, scan_directory


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


runner = CliRunner()


def _make_image(
    output_dir: Path,
    name: str,
    size: tuple[int, int] = (200, 200),
    color: tuple[int, int, int] = (100, 150, 200),
    fmt: str = "JPEG",
    subdir: str | None = None,
) -> Path:
    d = output_dir if subdir is None else output_dir / subdir
    d.mkdir(parents=True, exist_ok=True)
    path = d / name
    img = Image.new("RGB", size, color)
    img.save(path, fmt, quality=90)
    return path


def _make_png(output_dir: Path, name: str, size: tuple[int, int] = (100, 100)) -> Path:
    path = output_dir / name
    Image.new("RGBA", size, (255, 0, 0, 128)).save(path, "PNG")
    return path


# ---------------------------------------------------------------------------
# scan_directory tests
# ---------------------------------------------------------------------------


def test_scan_empty_directory(output_dir: Path) -> None:
    empty_dir = output_dir / "empty"
    empty_dir.mkdir(parents=True, exist_ok=True)
    report = scan_directory(empty_dir)

    assert isinstance(report, ScanReport)
    assert report.total_files == 0
    assert report.valid_images == 0
    assert report.errors == 0
    assert report.total_size_bytes == 0
    assert report.entries == []
    assert report.formats == {}


def test_scan_single_jpeg(output_dir: Path) -> None:
    _make_image(output_dir, "photo.jpg", (800, 600))
    report = scan_directory(output_dir)

    assert report.total_files == 1
    assert report.valid_images == 1
    assert report.errors == 0
    assert report.total_size_bytes > 0
    assert "JPEG" in report.formats
    assert report.formats["JPEG"] == 1

    entry = report.entries[0]
    assert isinstance(entry, ScanEntry)
    assert entry.width == 800
    assert entry.height == 600
    assert entry.format == "JPEG"
    assert entry.error is None
    assert entry.file_path.name == "photo.jpg"


def test_scan_multiple_formats(output_dir: Path) -> None:
    _make_image(output_dir, "a.jpg", (400, 300))
    _make_png(output_dir, "b.png", (200, 200))
    _make_image(output_dir, "c.webp", (300, 300), fmt="WEBP")

    report = scan_directory(output_dir)

    assert report.total_files == 3
    assert report.valid_images == 3
    assert "JPEG" in report.formats
    assert "PNG" in report.formats
    assert "WEBP" in report.formats


def test_scan_recursive(output_dir: Path) -> None:
    _make_image(output_dir, "top.jpg", (400, 300))
    _make_image(output_dir, "sub.png", (200, 200), fmt="PNG", subdir="sub")

    # Non-recursive: only top-level
    report_flat = scan_directory(output_dir, recursive=False)
    assert report_flat.total_files == 1

    # Recursive: both
    report_recursive = scan_directory(output_dir, recursive=True)
    assert report_recursive.total_files == 2
    names = {e.file_path.name for e in report_recursive.entries}
    assert "top.jpg" in names
    assert "sub.png" in names


def test_scan_directory_max_entries(output_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pixopt.inventory.MAX_SCAN_ENTRIES", 1)
    _make_image(output_dir, "a.jpg", (200, 200))
    _make_image(output_dir, "b.jpg", (200, 200))

    report = scan_directory(output_dir)
    assert report.total_files == 1
    assert report.valid_images == 1


def test_scan_corrupt_file(output_dir: Path) -> None:
    _make_image(output_dir, "good.jpg", (200, 200))
    corrupt = output_dir / "corrupt.jpg"
    corrupt.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    report = scan_directory(output_dir)

    assert report.total_files == 2
    assert report.valid_images == 1
    assert report.errors == 1

    corrupt_entry = next(e for e in report.entries if e.file_path.name == "corrupt.jpg")
    assert corrupt_entry.error is not None
    assert corrupt_entry.width == 0


def test_scan_nonexistent_directory_raises(output_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        scan_directory(output_dir / "nonexistent")


def test_scan_alpha_detection(output_dir: Path) -> None:
    _make_png(output_dir, "alpha.png", (100, 100))
    report = scan_directory(output_dir)

    entry = report.entries[0]
    assert entry.has_alpha is True


def test_scan_no_alpha(output_dir: Path) -> None:
    _make_image(output_dir, "no_alpha.jpg", (100, 100))
    report = scan_directory(output_dir)

    entry = report.entries[0]
    assert entry.has_alpha is False


def test_scan_animated_gif(output_dir: Path) -> None:
    frames = [Image.new("RGB", (50, 50), (i * 50, 0, 0)) for i in range(3)]
    gif_path = output_dir / "anim.gif"
    frames[0].save(gif_path, "GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)

    report = scan_directory(output_dir)

    entry = report.entries[0]
    assert entry.is_animated is True
    assert entry.frame_count == 3


def test_scan_largest_smallest(output_dir: Path) -> None:
    _make_image(output_dir, "small.jpg", (50, 50))
    _make_image(output_dir, "large.jpg", (2000, 2000))

    report = scan_directory(output_dir)

    assert report.largest_file is not None
    assert report.largest_file.name == "large.jpg"
    assert report.largest_size > report.smallest_size
    assert report.smallest_file is not None
    assert report.smallest_file.name == "small.jpg"


def test_scan_extensions_filter(output_dir: Path) -> None:
    _make_image(output_dir, "a.jpg", (100, 100))
    _make_png(output_dir, "b.png", (100, 100))

    report = scan_directory(output_dir, extensions=[".jpg"])
    assert report.total_files == 1
    assert report.entries[0].file_path.name == "a.jpg"


def test_scan_report_to_dict_serializable(output_dir: Path) -> None:
    _make_image(output_dir, "a.jpg", (200, 200))
    report = scan_directory(output_dir)

    d = report.to_dict()
    assert isinstance(d, dict)
    assert isinstance(d["entries"], list)
    assert isinstance(d["entries"][0], dict)
    # Must be JSON-serializable
    json.dumps(d)


def test_scan_entry_to_dict(output_dir: Path) -> None:
    _make_image(output_dir, "a.jpg", (200, 200))
    report = scan_directory(output_dir)

    entry = report.entries[0]
    d = entry.to_dict()
    assert d["file_path"] == str(entry.file_path)
    assert d["width"] == 200
    assert d["format"] == "JPEG"
    json.dumps(d)


def test_scan_entry_human_file_size(output_dir: Path) -> None:
    _make_image(output_dir, "a.jpg", (200, 200))
    report = scan_directory(output_dir)

    entry = report.entries[0]
    size_str = entry.human_file_size
    assert "B" in size_str or "KB" in size_str


def test_scan_report_human_total_size(output_dir: Path) -> None:
    _make_image(output_dir, "a.jpg", (200, 200))
    report = scan_directory(output_dir)

    size_str = report.human_total_size
    assert "B" in size_str or "KB" in size_str


def test_scan_empty(output_dir: Path) -> None:
    report = scan_directory(output_dir)

    assert report.total_files == 0
    assert report.valid_images == 0
    assert report.smallest_file is None
    assert report.smallest_size == 0
    assert report.largest_file is None
    assert report.largest_size == 0


def test_scan_largest_smallest_different_order(output_dir: Path) -> None:
    # Create the larger file first so the initial smallest value is not the true minimum.
    _make_image(output_dir, "large.jpg", (2000, 2000), color=(200, 0, 0))
    _make_image(output_dir, "small.jpg", (50, 50), color=(0, 200, 0))

    report = scan_directory(output_dir)

    assert report.smallest_file is not None
    assert report.smallest_file.name == "small.jpg"
    assert report.largest_file is not None
    assert report.largest_file.name == "large.jpg"
    assert report.smallest_size < report.largest_size


def test_scan_directory_rejects_parent_reference(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="parent"):
        scan_directory(tmp_path / ".." / "outside")


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_scan_basic(output_dir: Path) -> None:
    _make_image(output_dir, "photo.jpg", (800, 600))
    result = runner.invoke(app, ["scan", str(output_dir)])

    assert result.exit_code == 0
    assert "photo.jpg" in result.output
    assert "JPEG" in result.output


def test_cli_scan_json_output(output_dir: Path) -> None:
    _make_image(output_dir, "photo.jpg", (800, 600))
    result = runner.invoke(app, ["scan", str(output_dir), "--json"])

    assert result.exit_code == 0
    # Output should be valid JSON
    output = result.stdout.strip()
    parsed = json.loads(output)
    assert parsed["total_files"] == 1
    assert parsed["valid_images"] == 1
    assert parsed["entries"][0]["format"] == "JPEG"


def test_cli_scan_recursive(output_dir: Path) -> None:
    _make_image(output_dir, "top.jpg", (200, 200))
    _make_image(output_dir, "sub.png", (100, 100), fmt="PNG", subdir="sub")

    result = runner.invoke(app, ["scan", str(output_dir), "--recursive"])

    assert result.exit_code == 0
    assert "top.jpg" in result.output
    assert "sub.png" in result.output


def test_cli_scan_non_recursive_excludes_subdir(output_dir: Path) -> None:
    _make_image(output_dir, "top.jpg", (200, 200))
    _make_image(output_dir, "sub.png", (100, 100), fmt="PNG", subdir="sub")

    result = runner.invoke(app, ["scan", str(output_dir)])

    assert result.exit_code == 0
    assert "top.jpg" in result.output
    assert "sub.png" not in result.output


def test_cli_scan_empty_directory(output_dir: Path) -> None:
    empty_dir = output_dir / "empty_cli"
    empty_dir.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(app, ["scan", str(empty_dir)])

    assert result.exit_code == 0
    assert "0" in result.output


def test_cli_scan_nonexistent_directory(output_dir: Path) -> None:
    result = runner.invoke(app, ["scan", str(output_dir / "nope")])

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower() or "error" in result.output.lower()
