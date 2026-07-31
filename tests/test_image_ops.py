"""Tests for advanced image operations (fit modes, anchors, EXIF orientation)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import piexif
import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli import app
from pixopt.image_ops import (
    _compute_target_size,
    apply_exif_orientation,
    parse_aspect_ratio,
    parse_color,
    resize_image,
)
from pixopt.models import Anchor, FitMode
from pixopt.optimizer import optimize_image

if TYPE_CHECKING:
    pass


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def wide_rgb() -> Image.Image:
    """Generate a wide 600x200 red->green gradient test image."""
    img = Image.new("RGB", (600, 200), (180, 0, 0))
    for x in range(600):
        for y in range(200):
            img.putpixel((x, y), (180 + x // 6, 0, 0))
    return img


@pytest.fixture
def tall_rgba() -> Image.Image:
    """Generate a tall 200x400 transparent image."""
    img = Image.new("RGBA", (200, 400), (0, 0, 255, 0))
    for y in range(400):
        for x in range(200):
            img.putpixel((x, y), (0, 0, 255, 255 - y // 2))
    return img


def test_parse_aspect_ratio() -> None:
    assert parse_aspect_ratio("16:9") == (16, 9)
    assert parse_aspect_ratio("4/3") == (4, 3)
    assert parse_aspect_ratio((3, 2)) == (3, 2)
    assert parse_aspect_ratio(None) is None

    with pytest.raises(ValueError):
        parse_aspect_ratio("invalid")
    with pytest.raises(ValueError):
        parse_aspect_ratio((0, 1))
    with pytest.raises(ValueError):
        parse_aspect_ratio((-1, 1))
    with pytest.raises(ValueError):
        parse_aspect_ratio("100000:1")
    with pytest.raises(ValueError):
        parse_aspect_ratio((1.5, 1))  # type: ignore[arg-type]


def test_parse_color() -> None:
    assert parse_color("white") == (255, 255, 255)
    assert parse_color("black") == (0, 0, 0)
    assert parse_color("#ffffff") == (255, 255, 255)
    assert parse_color("#fff") == (255, 255, 255)
    assert parse_color((128, 64, 32)) == (128, 64, 32)

    with pytest.raises(ValueError):
        parse_color("not-a-color")
    with pytest.raises(ValueError):
        parse_color("#ff")
    with pytest.raises(ValueError):
        parse_color("#ff00ff00")
    with pytest.raises(ValueError):
        parse_color((256, 0, 0))
    with pytest.raises(ValueError):
        parse_color((1.5, 0, 0))  # type: ignore[arg-type]


def test_resize_image_fit_fill(wide_rgb: Image.Image) -> None:
    resized = resize_image(wide_rgb, max_width=200, max_height=100, fit=FitMode.FILL)
    assert resized.size == (200, 100)


def test_resize_image_fit_down(wide_rgb: Image.Image) -> None:
    resized = resize_image(wide_rgb, max_width=200, max_height=100, fit=FitMode.DOWN)
    assert resized.width <= 200
    assert resized.height <= 100


def test_resize_image_fit_cover(wide_rgb: Image.Image) -> None:
    resized = resize_image(
        wide_rgb,
        max_width=200,
        max_height=200,
        fit=FitMode.COVER,
        anchor=Anchor.CENTER,
    )
    assert resized.size == (200, 200)


def test_resize_image_fit_contain_with_padding(wide_rgb: Image.Image) -> None:
    resized = resize_image(
        wide_rgb,
        max_width=300,
        max_height=300,
        fit=FitMode.CONTAIN,
        anchor=Anchor.CENTER,
        background_color=(0, 255, 0),
    )
    assert resized.size == (300, 300)


def test_resize_image_aspect_ratio(wide_rgb: Image.Image) -> None:
    resized = resize_image(
        wide_rgb,
        max_width=400,
        max_height=400,
        fit=FitMode.COVER,
        aspect_ratio="1:1",
        anchor=Anchor.TOP,
    )
    assert resized.size == (400, 400)


def test_compute_target_size_rejects_zero_aspect_ratio() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        _compute_target_size(100, 100, 200, 200, (0, 1))
    with pytest.raises(ValueError, match="must be positive"):
        _compute_target_size(100, 100, 200, 200, (-1, 1))
    with pytest.raises(ValueError, match="must be positive"):
        _compute_target_size(100, 100, 200, 200, (1, -1))


def test_resize_image_transparent_contain(tall_rgba: Image.Image) -> None:
    resized = resize_image(
        tall_rgba,
        max_width=100,
        max_height=100,
        fit=FitMode.CONTAIN,
        background_color=(255, 0, 0),
    )
    assert resized.size == (100, 100)
    assert resized.mode == "RGB"


def test_resize_image_anchor_top_bottom(wide_rgb: Image.Image) -> None:
    cover_top = resize_image(
        wide_rgb,
        max_width=200,
        max_height=200,
        fit=FitMode.COVER,
        anchor=Anchor.TOP,
    )
    cover_bottom = resize_image(
        wide_rgb,
        max_width=200,
        max_height=200,
        fit=FitMode.COVER,
        anchor=Anchor.BOTTOM,
    )
    assert cover_top.size == cover_bottom.size == (200, 200)


def test_face_anchor_fallback(wide_rgb: Image.Image) -> None:
    resized = resize_image(
        wide_rgb,
        max_width=200,
        max_height=200,
        fit=FitMode.COVER,
        anchor=Anchor.FACE,
    )
    assert resized.size == (200, 200)


def _write_with_orientation(img: Image.Image, path: Path, orientation: int) -> None:
    """Save a JPEG with a custom EXIF orientation tag."""
    # Build minimal EXIF dict. Orientation tag is under the 0th IFD.
    exif_ifd = {piexif.ImageIFD.Orientation: orientation}
    exif_dict = {"0th": exif_ifd, "Exif": {}, "GPS": {}, "1st": {}}
    exif_bytes = piexif.dump(exif_dict)
    img.save(path, "JPEG", exif=exif_bytes)


def test_apply_exif_orientation(output_dir: Path) -> None:
    source = output_dir / "oriented_source.jpg"
    expected = output_dir / "oriented_expected.jpg"
    rotated = output_dir / "oriented_applied.jpg"

    img = Image.new("RGB", (400, 200), (128, 0, 0))
    _write_with_orientation(img, source, 6)  # 90° CW

    with Image.open(source) as loaded:
        loaded.load()
        corrected = apply_exif_orientation(loaded)
        # Orientation 6 means the raw data is rotated 90° CW, so after
        # correction the width/height should be swapped back.
        assert corrected.size == (200, 400)
        corrected.save(expected, "JPEG")

    result = optimize_image(
        source,
        rotated,
        max_width=100,
        fit=FitMode.COVER,
        auto_orient=True,
        strip_metadata=False,
    )
    assert result.success
    with Image.open(result.output_path) as out:
        assert out.size == (100, 200)


def test_optimize_image_with_fit_cover(output_dir: Path) -> None:
    source = output_dir / "cover_source.jpg"
    output = output_dir / "cover_output.jpg"
    img = Image.new("RGB", (600, 300), (64, 128, 192))
    img.save(source, "JPEG")

    result = optimize_image(
        source,
        output,
        max_width=300,
        max_height=300,
        fit=FitMode.COVER,
        anchor=Anchor.CENTER,
        quality=90,
    )
    assert result.success
    with Image.open(result.output_path) as out:
        assert out.size == (300, 300)


def test_optimize_image_with_fit_contain(output_dir: Path) -> None:
    source = output_dir / "contain_source.jpg"
    output = output_dir / "contain_output.jpg"
    img = Image.new("RGB", (600, 300), (64, 128, 192))
    img.save(source, "JPEG")

    result = optimize_image(
        source,
        output,
        max_width=400,
        max_height=400,
        fit=FitMode.CONTAIN,
        anchor=Anchor.TOP,
        background_color="#00ff00",
        quality=90,
    )
    assert result.success
    with Image.open(result.output_path) as out:
        assert out.size == (400, 400)


def test_optimize_image_aspect_ratio(output_dir: Path) -> None:
    source = output_dir / "aspect_source.jpg"
    output = output_dir / "aspect_output.jpg"
    img = Image.new("RGB", (600, 400), (192, 64, 128))
    img.save(source, "JPEG")

    result = optimize_image(
        source,
        output,
        max_width=300,
        max_height=300,
        fit=FitMode.COVER,
        aspect_ratio="16:9",
        anchor=Anchor.CENTER,
    )
    assert result.success
    with Image.open(result.output_path) as out:
        assert out.size[0] == 300
        assert abs(out.size[1] - 168) <= 1


def test_optimize_image_auto_orient_disabled(output_dir: Path) -> None:
    source = output_dir / "no_orient_source.jpg"
    output = output_dir / "no_orient_output.jpg"
    img = Image.new("RGB", (400, 200), (128, 0, 0))
    _write_with_orientation(img, source, 6)

    result = optimize_image(
        source,
        output,
        max_width=100,
        fit=FitMode.FILL,
        auto_orient=False,
    )
    assert result.success
    with Image.open(result.output_path) as out:
        # Without auto-orient, the raw dimensions are kept before resize.
        assert out.size == (100, 50)


def test_cli_optimize_fit_cover(output_dir: Path) -> None:
    runner = CliRunner()
    source = output_dir / "cover_source.jpg"
    img = Image.new("RGB", (600, 300), (64, 128, 192))
    img.save(source, "JPEG")
    output = output_dir / "cli_cover.jpg"
    result = runner.invoke(
        app,
        [
            "optimize",
            str(source),
            str(output),
            "--fit",
            "cover",
            "--width",
            "120",
            "--height",
            "120",
            "--anchor",
            "center",
            "--quality",
            "90",
        ],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()
    with Image.open(output) as img:
        assert img.size == (120, 120)


def test_cli_convert_fit_contain(output_dir: Path) -> None:
    runner = CliRunner()
    source = output_dir / "contain_source.jpg"
    img = Image.new("RGB", (600, 300), (64, 128, 192))
    img.save(source, "JPEG")
    output = output_dir / "cli_contain.jpg"
    result = runner.invoke(
        app,
        [
            "convert",
            str(source),
            str(output),
            "--fit",
            "contain",
            "--width",
            "200",
            "--height",
            "200",
            "--anchor",
            "top",
            "--background-color",
            "#ff0000",
        ],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()
    with Image.open(output) as img:
        assert img.size == (200, 200)
