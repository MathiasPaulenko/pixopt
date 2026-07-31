"""Tests for asset bundle generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt._units import (
    MAX_BUNDLE_PALETTE_N,
    MAX_FAVICON_SIZES,
    MAX_IMAGE_DIMENSION,
    MAX_SRCSET_WIDTHS,
)
from pixopt.bundle import AssetBundle, BundleOptions, generate_asset_bundle
from pixopt.cli import app


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_source(
    output_dir: Path, name: str = "source.jpg", size: tuple[int, int] = (2000, 1500)
) -> Path:
    path = output_dir / name
    img = Image.new("RGB", size, (100, 150, 200))
    # Add some variation for palette extraction.
    pixels = img.load()
    assert pixels is not None
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = (
                (x * 255) // size[0],
                (y * 255) // size[1],
                128,
            )
    img.save(path, "JPEG", quality=95)
    return path


# ---------------------------------------------------------------------------
# BundleOptions tests
# ---------------------------------------------------------------------------


def test_bundle_options_defaults() -> None:
    opts = BundleOptions()
    assert opts.hero_width == 1920
    assert opts.thumbnail_width == 300
    assert opts.og_width == 1200
    assert opts.og_height == 630
    assert opts.palette_n == 6
    assert opts.generate_hero is True
    assert opts.generate_favicon is True


def test_bundle_options_custom() -> None:
    opts = BundleOptions(
        hero_width=800,
        thumbnail_width=100,
        generate_favicon=False,
        palette_n=4,
    )
    assert opts.hero_width == 800
    assert opts.thumbnail_width == 100
    assert opts.generate_favicon is False
    assert opts.palette_n == 4


# ---------------------------------------------------------------------------
# generate_asset_bundle tests
# ---------------------------------------------------------------------------


def test_generate_bundle_full(output_dir: Path) -> None:
    source = _make_source(output_dir)
    out_dir = output_dir / "full"
    result = generate_asset_bundle(source, out_dir)

    assert isinstance(result, AssetBundle)
    assert result.hero is not None
    assert result.hero.success
    assert result.hero.output_path.exists()

    assert result.thumbnail is not None
    assert result.thumbnail.success
    assert result.thumbnail.output_path.exists()

    assert result.og_image is not None
    assert result.og_image.success
    assert result.og_image.output_path.exists()

    assert result.favicon is not None
    assert result.favicon.success
    assert result.favicon.output_path.exists()

    assert len(result.srcset_images) > 0
    for s in result.srcset_images:
        assert s.output_path.exists()

    assert result.lqip_data_uri is not None
    assert result.lqip_data_uri.startswith("data:image/jpeg;base64,")

    assert result.blurhash is not None
    assert len(result.blurhash) > 0

    assert result.dominant_color is not None
    assert result.dominant_color.startswith("#")

    assert result.palette is not None
    assert len(result.palette.colors) > 0


def test_generate_bundle_selective(output_dir: Path) -> None:
    source = _make_source(output_dir)
    out_dir = output_dir / "selective"
    opts = BundleOptions(
        generate_hero=True,
        generate_thumbnail=False,
        generate_og=False,
        generate_favicon=False,
        generate_srcset=False,
        generate_lqip=True,
        generate_blurhash=False,
        generate_palette=False,
        generate_dominant_color=False,
    )
    result = generate_asset_bundle(source, out_dir, options=opts)

    assert result.hero is not None
    assert result.thumbnail is None
    assert result.og_image is None
    assert result.favicon is None
    assert len(result.srcset_images) == 0
    assert result.lqip_data_uri is not None
    assert result.blurhash is None
    assert result.dominant_color is None
    assert result.palette is None


def test_generate_bundle_only_palette(output_dir: Path) -> None:
    source = _make_source(output_dir)
    out_dir = output_dir / "palette_only"
    opts = BundleOptions(
        generate_hero=False,
        generate_thumbnail=False,
        generate_og=False,
        generate_favicon=False,
        generate_srcset=False,
        generate_lqip=False,
        generate_blurhash=False,
        generate_palette=True,
        generate_dominant_color=False,
    )
    result = generate_asset_bundle(source, out_dir, options=opts)

    assert result.hero is None
    assert result.palette is not None
    assert len(result.palette.colors) > 0


def test_generate_bundle_to_dict_serializable(output_dir: Path) -> None:
    source = _make_source(output_dir)
    out_dir = output_dir / "dict"
    result = generate_asset_bundle(source, out_dir)
    d = result.to_dict()

    assert isinstance(d, dict)
    assert isinstance(d["source_path"], str)
    assert isinstance(d["output_dir"], str)
    assert d["hero"] is not None
    assert d["lqip_data_uri"] is not None
    assert d["blurhash"] is not None
    assert d["dominant_color"] is not None
    assert d["palette"] is not None
    json.dumps(d)


def test_generate_bundle_file_not_found(output_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        generate_asset_bundle("nonexistent.jpg", output_dir / "error")


def test_generate_bundle_custom_widths(output_dir: Path) -> None:
    source = _make_source(output_dir)
    out_dir = output_dir / "custom"
    opts = BundleOptions(
        hero_width=500,
        thumbnail_width=80,
        srcset_widths=[100, 200, 400],
        generate_og=False,
        generate_favicon=False,
        generate_lqip=False,
        generate_blurhash=False,
        generate_palette=False,
        generate_dominant_color=False,
    )
    result = generate_asset_bundle(source, out_dir, options=opts)

    assert result.hero is not None
    assert result.hero.width <= 500

    assert result.thumbnail is not None
    assert result.thumbnail.width <= 80

    assert len(result.srcset_images) > 0
    widths = [s.width for s in result.srcset_images]
    assert all(w <= 400 for w in widths)


def test_generate_bundle_creates_output_dir(output_dir: Path) -> None:
    source = _make_source(output_dir)
    out_dir = output_dir / "auto_created" / "nested"
    _ = generate_asset_bundle(source, out_dir)
    assert out_dir.exists()


# ---------------------------------------------------------------------------
# CLI bundle command tests
# ---------------------------------------------------------------------------


def test_cli_bundle_basic(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    out_dir = output_dir / "cli_basic"
    result = runner.invoke(app, ["bundle", str(source), "-o", str(out_dir)])
    assert result.exit_code == 0
    assert "Hero" in result.output
    assert "Thumbnail" in result.output
    assert "og:image" in result.output
    assert "Favicon" in result.output
    assert "Srcset" in result.output
    assert "LQIP" in result.output
    assert "Blurhash" in result.output
    assert "Dominant color" in result.output
    assert "Palette" in result.output


def test_cli_bundle_json_output(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    out_dir = output_dir / "cli_json"
    result = runner.invoke(app, ["bundle", str(source), "-o", str(out_dir), "--output", "json"])
    assert result.exit_code == 0
    assert '"hero"' in result.output or "'hero'" in result.output
    assert '"lqip_data_uri"' in result.output or "'lqip_data_uri'" in result.output
    assert '"palette"' in result.output or "'palette'" in result.output


def test_cli_bundle_skip_assets(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    out_dir = output_dir / "cli_skip"
    result = runner.invoke(
        app,
        [
            "bundle",
            str(source),
            "-o",
            str(out_dir),
            "--no-favicon",
            "--no-srcset",
            "--no-blurhash",
        ],
    )
    assert result.exit_code == 0
    assert "Favicon" not in result.output
    assert "Srcset" not in result.output
    assert "Blurhash" not in result.output


def test_cli_bundle_nonexistent_file(output_dir: Path) -> None:
    runner = CliRunner()
    out_dir = output_dir / "cli_error"
    result = runner.invoke(app, ["bundle", "nonexistent.jpg", "-o", str(out_dir)])
    assert result.exit_code != 0


def test_cli_bundle_custom_quality(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    out_dir = output_dir / "cli_quality"
    result = runner.invoke(
        app,
        ["bundle", str(source), "-o", str(out_dir), "--quality", "50", "--output", "json"],
    )
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Security / resource limit tests
# ---------------------------------------------------------------------------


def test_generate_bundle_output_dir_parent_reference_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100), (100, 150, 200)).save(source, "JPEG")
    output_dir = tmp_path / "out" / ".."

    with pytest.raises(ValueError, match="parent"):
        _ = generate_asset_bundle(source, output_dir)


def test_bundle_options_hero_width_too_large() -> None:
    with pytest.raises(ValueError, match="hero_width must be between"):
        BundleOptions(hero_width=MAX_IMAGE_DIMENSION + 1)


def test_bundle_options_og_width_too_large() -> None:
    with pytest.raises(ValueError, match="og_width must be between"):
        BundleOptions(og_width=MAX_IMAGE_DIMENSION + 1)


def test_bundle_options_lqip_size_too_large() -> None:
    with pytest.raises(ValueError, match="lqip_size must be between"):
        BundleOptions(lqip_size=MAX_IMAGE_DIMENSION + 1)


def test_bundle_options_srcset_widths_too_many() -> None:
    with pytest.raises(ValueError, match="srcset_widths must not exceed"):
        BundleOptions(srcset_widths=list(range(1, MAX_SRCSET_WIDTHS + 2)))


def test_bundle_options_srcset_width_too_large() -> None:
    with pytest.raises(ValueError, match="srcset width must be between"):
        BundleOptions(srcset_widths=[MAX_IMAGE_DIMENSION + 1])


def test_bundle_options_favicon_size_too_large() -> None:
    with pytest.raises(ValueError, match="favicon size must be between"):
        BundleOptions(favicon_sizes=[MAX_IMAGE_DIMENSION + 1])


def test_bundle_options_palette_n_too_large() -> None:
    with pytest.raises(ValueError, match="palette_n must be between"):
        BundleOptions(palette_n=MAX_BUNDLE_PALETTE_N + 1)


def test_bundle_options_favicon_sizes_too_many() -> None:
    with pytest.raises(ValueError, match="favicon_sizes must not exceed"):
        BundleOptions(favicon_sizes=[1] * (MAX_FAVICON_SIZES + 1))
