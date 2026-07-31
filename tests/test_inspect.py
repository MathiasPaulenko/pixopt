"""Tests for structured image metadata inspection (inspect_image)."""

from __future__ import annotations

import json
from pathlib import Path

import piexif
import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli import app
from pixopt.inspect import inspect_image
from pixopt.models import ImageInfo


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_inspect_basic_jpeg(output_dir: Path) -> None:
    path = output_dir / "basic.jpg"
    Image.new("RGB", (800, 600), (200, 100, 50)).save(path, "JPEG", quality=90)

    info = inspect_image(path)
    assert isinstance(info, ImageInfo)
    assert info.width == 800
    assert info.height == 600
    assert info.mode == "RGB"
    assert info.format == "JPEG"
    assert info.has_alpha is False
    assert info.is_animated is False
    assert info.frame_count == 1
    assert info.icc_profile is False
    assert info.orientation is None


def test_inspect_png_with_alpha(output_dir: Path) -> None:
    path = output_dir / "alpha.png"
    Image.new("RGBA", (400, 300), (10, 20, 30, 255)).save(path, "PNG")

    info = inspect_image(path)
    assert info.mode == "RGBA"
    assert info.has_alpha is True
    assert info.format == "PNG"


def test_inspect_animated_gif(output_dir: Path) -> None:
    path = output_dir / "animated.gif"
    frames = [Image.new("RGB", (100, 100), (i * 50, i * 30, i * 10)) for i in range(5)]
    frames[0].save(path, "GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)

    info = inspect_image(path)
    assert info.is_animated is True
    assert info.frame_count == 5


def test_inspect_with_exif_orientation(output_dir: Path) -> None:
    path = output_dir / "oriented.jpg"
    img = Image.new("RGB", (400, 200), (128, 0, 0))
    exif_ifd = {piexif.ImageIFD.Orientation: 6}
    exif_dict = {"0th": exif_ifd, "Exif": {}, "GPS": {}, "1st": {}}
    exif_bytes = piexif.dump(exif_dict)
    img.save(path, "JPEG", exif=exif_bytes)

    info = inspect_image(path)
    assert info.orientation == 6
    assert "Orientation" in info.exif


def test_inspect_dpi(output_dir: Path) -> None:
    path = output_dir / "dpi.png"
    img = Image.new("RGB", (200, 200), (0, 128, 0))
    img.save(path, "PNG", dpi=(300, 300))

    info = inspect_image(path)
    assert info.dpi is not None
    assert abs(info.dpi[0] - 300.0) < 1.0
    assert abs(info.dpi[1] - 300.0) < 1.0


def test_inspect_no_dpi(output_dir: Path) -> None:
    path = output_dir / "nodpi.jpg"
    Image.new("RGB", (100, 100), (50, 50, 50)).save(path, "JPEG")

    info = inspect_image(path)
    assert info.dpi is None


def test_inspect_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        inspect_image("nonexistent_file.jpg")


def test_inspect_corrupt_file(output_dir: Path) -> None:
    path = output_dir / "corrupt.jpg"
    path.write_bytes(b"not an image at all")

    from PIL import UnidentifiedImageError

    with pytest.raises(UnidentifiedImageError):
        inspect_image(path)


def test_inspect_to_dict_serializable(output_dir: Path) -> None:
    path = output_dir / "serial.jpg"
    Image.new("RGB", (300, 200), (1, 2, 3)).save(path, "JPEG")

    info = inspect_image(path)
    d = info.to_dict()
    assert isinstance(d, dict)
    assert d["width"] == 300
    assert d["height"] == 200
    assert isinstance(d["file_path"], str)
    # Should be JSON-serializable.
    json.dumps(d, default=str)


def test_inspect_human_file_size(output_dir: Path) -> None:
    path = output_dir / "size.jpg"
    Image.new("RGB", (100, 100), (0, 0, 0)).save(path, "JPEG", quality=10)
    info = inspect_image(path)
    assert "B" in info.human_file_size or "KB" in info.human_file_size


# ---------------------------------------------------------------------------
# CLI info command tests
# ---------------------------------------------------------------------------


def test_cli_info_basic(output_dir: Path) -> None:
    runner = CliRunner()
    path = output_dir / "cli_basic.jpg"
    Image.new("RGB", (800, 600), (200, 100, 50)).save(path, "JPEG", quality=90)

    result = runner.invoke(app, ["info", str(path)])
    assert result.exit_code == 0
    assert "JPEG" in result.output
    assert "800x600" in result.output


def test_cli_info_json_output(output_dir: Path) -> None:
    runner = CliRunner()
    path = output_dir / "cli_json.jpg"
    Image.new("RGB", (400, 300), (10, 20, 30)).save(path, "JPEG", quality=85)

    result = runner.invoke(app, ["info", str(path), "--json"])
    assert result.exit_code == 0
    # The output should contain valid JSON.
    assert '"width": 400' in result.output or "'width': 400" in result.output


def test_cli_info_alpha_png(output_dir: Path) -> None:
    runner = CliRunner()
    path = output_dir / "cli_alpha.png"
    Image.new("RGBA", (200, 200), (255, 0, 0, 128)).save(path, "PNG")

    result = runner.invoke(app, ["info", str(path)])
    assert result.exit_code == 0
    assert "RGBA" in result.output
    assert "Yes" in result.output  # Has alpha: Yes


def test_cli_info_animated_gif(output_dir: Path) -> None:
    runner = CliRunner()
    path = output_dir / "cli_animated.gif"
    frames = [Image.new("RGB", (50, 50), (i * 80, i * 40, i * 20)) for i in range(3)]
    frames[0].save(path, "GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)

    result = runner.invoke(app, ["info", str(path)])
    assert result.exit_code == 0
    assert "Yes" in result.output  # Animated: Yes
    assert "3 frames" in result.output


def test_cli_info_nonexistent_file() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["info", "nonexistent.jpg"])
    assert result.exit_code != 0
