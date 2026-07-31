"""Tests for color palette extraction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli import app
from pixopt.palette import ColorSwatch, PaletteResult, extract_palette


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_gradient(output_dir: Path, name: str, size: tuple[int, int] = (200, 200)) -> Path:
    """Create a gradient image with distinct color regions."""
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size)
    pixels = img.load()
    assert pixels is not None
    for y in range(size[1]):
        for x in range(size[0]):
            if x < size[0] // 3:
                pixels[x, y] = (255, 0, 0)  # red
            elif x < size[0] * 2 // 3:
                pixels[x, y] = (0, 255, 0)  # green
            else:
                pixels[x, y] = (0, 0, 255)  # blue
    img.save(path, "PNG")
    return path


def _make_solid(
    output_dir: Path, name: str, color: tuple[int, int, int], size: tuple[int, int] = (100, 100)
) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, "PNG")
    return path


# ---------------------------------------------------------------------------
# extract_palette unit tests
# ---------------------------------------------------------------------------


def test_extract_palette_basic(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "gradient.png")
    result = extract_palette(source, n=3)
    assert isinstance(result, PaletteResult)
    assert len(result.colors) == 3
    assert result.width == 200
    assert result.height == 200


def test_extract_palette_returns_swatch_objects(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "gradient2.png")
    result = extract_palette(source, n=3)
    for c in result.colors:
        assert isinstance(c, ColorSwatch)
        assert c.hex.startswith("#")
        assert len(c.hex) == 7
        assert len(c.rgb) == 3
        assert all(0 <= v <= 255 for v in c.rgb)
        assert c.percent >= 0.0


def test_extract_palette_sorted_by_frequency(output_dir: Path) -> None:
    # Create an image that's 80% red, 20% blue.
    path = output_dir / "dominant.png"
    img = Image.new("RGB", (100, 100))
    pixels = img.load()
    assert pixels is not None
    for y in range(100):
        for x in range(100):
            if x < 80:
                pixels[x, y] = (255, 0, 0)
            else:
                pixels[x, y] = (0, 0, 255)
    img.save(path, "PNG")

    result = extract_palette(path, n=2)
    assert len(result.colors) >= 2
    # The most dominant color should be red-ish.
    top = result.colors[0]
    assert top.rgb[0] > top.rgb[2]  # more red than blue


def test_extract_palette_solid_color(output_dir: Path) -> None:
    source = _make_solid(output_dir, "solid.png", (128, 64, 32))
    result = extract_palette(source, n=1)
    assert len(result.colors) >= 1
    c = result.colors[0]
    # Should be close to the solid color.
    assert abs(c.rgb[0] - 128) <= 5
    assert abs(c.rgb[1] - 64) <= 5
    assert abs(c.rgb[2] - 32) <= 5


def test_extract_palette_hex_format(output_dir: Path) -> None:
    source = _make_solid(output_dir, "hex.png", (255, 0, 128))
    result = extract_palette(source, n=1)
    c = result.colors[0]
    assert c.hex == "#ff0080"


def test_extract_palette_default_n(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "default_n.png")
    result = extract_palette(source)
    assert len(result.colors) <= 6
    assert len(result.colors) >= 1


def test_extract_palette_custom_n(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "custom_n.png")
    result = extract_palette(source, n=8)
    assert len(result.colors) <= 8


def test_extract_palette_to_dict_serializable(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "dict.png")
    result = extract_palette(source, n=3)
    d = result.to_dict()
    assert isinstance(d, dict)
    assert isinstance(d["source_path"], str)
    assert isinstance(d["colors"], list)
    assert isinstance(d["colors"][0]["rgb"], list)
    json.dumps(d)


def test_extract_palette_swatch_to_dict() -> None:
    sw = ColorSwatch(hex="#ff0000", rgb=(255, 0, 0), percent=50.0)
    d = sw.to_dict()
    assert d["hex"] == "#ff0000"
    assert d["rgb"] == [255, 0, 0]
    assert d["percent"] == 50.0


def test_extract_palette_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        extract_palette("nonexistent.png")


def test_extract_palette_invalid_n(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "invalid_n.png")
    with pytest.raises(ValueError):
        extract_palette(source, n=0)
    with pytest.raises(ValueError):
        extract_palette(source, n=33)


def test_extract_palette_corrupt_file(output_dir: Path) -> None:
    path = output_dir / "corrupt.png"
    path.write_bytes(b"not an image")
    from PIL import UnidentifiedImageError

    with pytest.raises(UnidentifiedImageError):
        extract_palette(path)


def test_extract_palette_percents_sum_approximately_100(output_dir: Path) -> None:
    source = _make_gradient(output_dir, "percents.png")
    result = extract_palette(source, n=3)
    total = sum(c.percent for c in result.colors)
    assert 95.0 <= total <= 105.0  # allow rounding tolerance


# ---------------------------------------------------------------------------
# CLI palette command tests
# ---------------------------------------------------------------------------


def test_cli_palette_basic(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_gradient(output_dir, "cli_basic.png")
    result = runner.invoke(app, ["palette", str(source), "-n", "3"])
    assert result.exit_code == 0
    assert "#" in result.output
    assert "rgb(" in result.output


def test_cli_palette_json_output(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_gradient(output_dir, "cli_json.png")
    result = runner.invoke(app, ["palette", str(source), "-n", "3", "--json"])
    assert result.exit_code == 0
    assert '"colors"' in result.output or "'colors'" in result.output
    assert '"hex"' in result.output or "'hex'" in result.output


def test_cli_palette_default_count(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_gradient(output_dir, "cli_default.png")
    result = runner.invoke(app, ["palette", str(source)])
    assert result.exit_code == 0


def test_cli_palette_nonexistent_file() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["palette", "nonexistent.png"])
    assert result.exit_code != 0
