"""Tests for sprite / contact sheet generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt._units import MAX_IMAGE_DIMENSION
from pixopt.cli.app import app
from pixopt.sprite import (
    SpriteResult,
    SpriteSlot,
    create_contact_sheet,
    create_sprite,
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
    size: tuple[int, int] = (100, 100),
    color: tuple[int, int, int] = (100, 150, 200),
    fmt: str = "PNG",
) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, fmt)
    return path


# ---------------------------------------------------------------------------
# create_sprite tests
# ---------------------------------------------------------------------------


def test_create_sprite_basic(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"img{i}.png") for i in range(4)]
    out = output_dir / "sprite.png"
    result = create_sprite(imgs, out)

    assert isinstance(result, SpriteResult)
    assert result.success
    assert result.total_images == 4
    assert out.exists()
    assert out.stat().st_size > 0


def test_create_sprite_grid_layout(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"g{i}.png") for i in range(6)]
    out = output_dir / "grid.png"
    result = create_sprite(imgs, out, layout="grid")

    assert result.success
    assert result.layout == "grid"
    # 6 images → 3x2 grid (auto)
    assert result.columns == 3
    assert result.rows == 2


def test_create_sprite_horizontal_layout(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"h{i}.png") for i in range(3)]
    out = output_dir / "horizontal.png"
    result = create_sprite(imgs, out, layout="horizontal")

    assert result.success
    assert result.layout == "horizontal"
    assert result.columns == 3
    assert result.rows == 1


def test_create_sprite_vertical_layout(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"v{i}.png") for i in range(3)]
    out = output_dir / "vertical.png"
    result = create_sprite(imgs, out, layout="vertical")

    assert result.success
    assert result.layout == "vertical"
    assert result.columns == 1
    assert result.rows == 3


def test_create_sprite_custom_columns(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"c{i}.png") for i in range(8)]
    out = output_dir / "custom_cols.png"
    result = create_sprite(imgs, out, columns=4)

    assert result.success
    assert result.columns == 4
    assert result.rows == 2


def test_create_sprite_cell_dimensions(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"s{i}.png", (150, 80)) for i in range(2)]
    out = output_dir / "cell_dims.png"
    result = create_sprite(imgs, out, cell_width=100, cell_height=100)

    assert result.success
    assert result.cell_width == 100
    assert result.cell_height == 100
    # Sheet should be 2 columns × 1 row
    assert result.width == 200
    assert result.height == 100


def test_create_sprite_auto_cell_dimensions(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"a{i}.png", (120, 90)) for i in range(4)]
    out = output_dir / "auto_cell.png"
    result = create_sprite(imgs, out)

    assert result.success
    # Auto cell = max image dimensions
    assert result.cell_width == 120
    assert result.cell_height == 90


def test_create_sprite_padding(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"p{i}.png", (50, 50)) for i in range(2)]
    out = output_dir / "padded.png"
    result = create_sprite(
        imgs, out, cell_width=50, cell_height=50, padding=10, layout="horizontal"
    )

    assert result.success
    # 2 cells × 50 + 1 gap × 10 = 110
    assert result.width == 110
    assert result.height == 50


def test_create_sprite_empty_list_raises(output_dir: Path) -> None:
    with pytest.raises(ValueError, match="images list cannot be empty"):
        create_sprite([], output_dir / "empty.png")


def test_create_sprite_creates_parent_dir(output_dir: Path) -> None:
    img = _make_image(output_dir, "parent.png")
    out = output_dir / "subdir" / "nested" / "sprite.png"
    result = create_sprite([img], out)

    assert result.success
    assert out.exists()


def test_create_sprite_jpeg_format(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"j{i}.png") for i in range(2)]
    out = output_dir / "sprite.jpg"
    result = create_sprite(imgs, out, fmt="JPEG")

    assert result.success
    with Image.open(out) as opened:
        assert opened.format == "JPEG"


def test_create_sprite_webp_format(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"w{i}.png") for i in range(2)]
    out = output_dir / "sprite.webp"
    result = create_sprite(imgs, out, fmt="WEBP")

    assert result.success
    with Image.open(out) as opened:
        assert opened.format == "WEBP"


def test_create_sprite_rgba_images(output_dir: Path) -> None:
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    path = output_dir / "rgba.png"
    img.save(path, "PNG")

    out = output_dir / "rgba_sprite.png"
    result = create_sprite([path], out)

    assert result.success
    assert out.exists()


def test_create_sprite_different_sizes(output_dir: Path) -> None:
    imgs = [
        _make_image(output_dir, "big.png", (200, 200)),
        _make_image(output_dir, "small.png", (50, 50)),
        _make_image(output_dir, "wide.png", (300, 100)),
    ]
    out = output_dir / "diff_sizes.png"
    result = create_sprite(imgs, out, cell_width=200, cell_height=200)

    assert result.success
    assert result.cell_width == 200
    assert result.cell_height == 200
    assert out.exists()


def test_create_sprite_slots_info(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"slot{i}.png") for i in range(4)]
    out = output_dir / "slots.png"
    result = create_sprite(imgs, out, cell_width=100, cell_height=100, columns=2)

    assert result.success
    assert len(result.slots) == 4
    for i, slot in enumerate(result.slots):
        assert isinstance(slot, SpriteSlot)
        assert slot.index == i
        assert slot.source == imgs[i]
        assert slot.width <= 100
        assert slot.height <= 100


def test_create_sprite_to_dict_serializable(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"d{i}.png") for i in range(2)]
    out = output_dir / "dict.png"
    result = create_sprite(imgs, out)

    d = result.to_dict()
    json.dumps(d)
    assert d["total_images"] == 2
    assert d["success"] is True
    assert isinstance(d["slots"], list)


def test_create_sprite_invalid_image(output_dir: Path) -> None:
    bad = output_dir / "bad.png"
    bad.write_bytes(b"not an image")
    out = output_dir / "bad_sprite.png"

    result = create_sprite([bad], out)
    assert not result.success
    assert result.error is not None


def test_create_sprite_single_image(output_dir: Path) -> None:
    img = _make_image(output_dir, "single.png")
    out = output_dir / "single_sprite.png"
    result = create_sprite([img], out)

    assert result.success
    assert result.total_images == 1
    assert result.columns == 1
    assert result.rows == 1


# ---------------------------------------------------------------------------
# create_contact_sheet tests
# ---------------------------------------------------------------------------


def test_contact_sheet_basic(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"cs{i}.png") for i in range(4)]
    out = output_dir / "contact.png"
    result = create_contact_sheet(imgs, out)

    assert result.success
    assert result.layout == "contact_sheet"
    assert result.total_images == 4
    assert out.exists()


def test_contact_sheet_grid_auto(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"csg{i}.png") for i in range(6)]
    out = output_dir / "contact_grid.png"
    result = create_contact_sheet(imgs, out)

    assert result.success
    assert result.columns == 3
    assert result.rows == 2


def test_contact_sheet_custom_columns(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"csc{i}.png") for i in range(8)]
    out = output_dir / "contact_cols.png"
    result = create_contact_sheet(imgs, out, columns=4)

    assert result.success
    assert result.columns == 4
    assert result.rows == 2


def test_contact_sheet_labels(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, "photo1.png"), _make_image(output_dir, "photo2.png")]
    out = output_dir / "labeled.png"
    result = create_contact_sheet(imgs, out)

    assert result.success
    # Check the output has reasonable dimensions (includes label area)
    assert result.height > result.cell_height * result.rows


def test_contact_sheet_empty_raises(output_dir: Path) -> None:
    with pytest.raises(ValueError, match="images list cannot be empty"):
        create_contact_sheet([], output_dir / "empty_cs.png")


def test_contact_sheet_to_dict_serializable(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"td{i}.png") for i in range(2)]
    out = output_dir / "cs_dict.png"
    result = create_contact_sheet(imgs, out)

    d = result.to_dict()
    json.dumps(d)
    assert d["layout"] == "contact_sheet"


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_sprite_basic(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"cli{i}.png") for i in range(4)]
    out = output_dir / "cli_sprite.png"

    result = runner.invoke(app, ["sprite", str(out), *[str(i) for i in imgs]])

    assert result.exit_code == 0
    assert "Sprite created" in result.output
    assert out.exists()


def test_cli_sprite_json(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"cj{i}.png") for i in range(2)]
    out = output_dir / "cli_json.png"

    result = runner.invoke(app, ["sprite", str(out), *[str(i) for i in imgs], "--json"])

    assert result.exit_code == 0
    parsed = json.loads(result.stdout.strip())
    assert parsed["total_images"] == 2
    assert parsed["success"] is True


def test_cli_sprite_layout_horizontal(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"lh{i}.png") for i in range(3)]
    out = output_dir / "cli_horizontal.png"

    result = runner.invoke(
        app,
        ["sprite", str(out), *[str(i) for i in imgs], "--layout", "horizontal"],
    )

    assert result.exit_code == 0
    assert "horizontal" in result.output


def test_cli_sprite_contact_sheet(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"cs_cli{i}.png") for i in range(4)]
    out = output_dir / "cli_contact.png"

    result = runner.invoke(
        app,
        ["sprite", str(out), *[str(i) for i in imgs], "--contact-sheet"],
    )

    assert result.exit_code == 0
    assert "contact_sheet" in result.output
    assert out.exists()


def test_cli_sprite_custom_cell_size(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"ccs{i}.png") for i in range(2)]
    out = output_dir / "cli_cell.png"

    result = runner.invoke(
        app,
        ["sprite", str(out), *[str(i) for i in imgs], "--cell-width", "80", "--cell-height", "80"],
    )

    assert result.exit_code == 0
    assert "80x80" in result.output


# ---------------------------------------------------------------------------
# Security / resource limit tests
# ---------------------------------------------------------------------------


def _make_tmp_image(path: Path, color: tuple[int, int, int] = (100, 150, 200)) -> Path:
    Image.new("RGB", (40, 40), color).save(path, "PNG")
    return path


def test_create_sprite_output_parent_reference_rejected(tmp_path: Path) -> None:
    img = _make_tmp_image(tmp_path / "img.png")
    output = tmp_path / ".." / "sprite.png"

    with pytest.raises(ValueError, match="parent"):
        create_sprite([img], output)


def test_create_contact_sheet_output_parent_reference_rejected(tmp_path: Path) -> None:
    img = _make_tmp_image(tmp_path / "img.png")
    output = tmp_path / ".." / "contact.png"

    with pytest.raises(ValueError, match="parent"):
        create_contact_sheet([img], output)


def test_create_sprite_cell_width_too_large() -> None:
    with pytest.raises(ValueError, match="cell_width must be between"):
        create_sprite([], Path("out.png"), cell_width=MAX_IMAGE_DIMENSION + 1)


def test_create_sprite_padding_too_large() -> None:
    with pytest.raises(ValueError, match="padding must be between"):
        create_sprite([], Path("out.png"), padding=MAX_IMAGE_DIMENSION + 1)


def test_create_sprite_too_many_images(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pixopt.sprite.MAX_SPRITE_IMAGES", 1)
    img1 = _make_tmp_image(tmp_path / "img1.png", (255, 0, 0))
    img2 = _make_tmp_image(tmp_path / "img2.png", (0, 255, 0))
    output = tmp_path / "sprite.png"

    with pytest.raises(ValueError, match="Too many"):
        create_sprite([img1, img2], output)


def test_create_sprite_sheet_too_large(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pixopt.sprite.MAX_IMAGE_DIMENSION", 50)
    img1 = _make_tmp_image(tmp_path / "img1.png", (255, 0, 0))
    img2 = _make_tmp_image(tmp_path / "img2.png", (0, 255, 0))
    output = tmp_path / "sprite.png"

    result = create_sprite([img1, img2], output, cell_width=40, layout="horizontal")

    assert not result.success
    assert result.error is not None
    assert "too large" in result.error or "dimensions" in result.error


def test_create_contact_sheet_too_many_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("pixopt.sprite.MAX_SPRITE_IMAGES", 1)
    img1 = _make_tmp_image(tmp_path / "img1.png", (255, 0, 0))
    img2 = _make_tmp_image(tmp_path / "img2.png", (0, 255, 0))
    output = tmp_path / "contact.png"

    with pytest.raises(ValueError, match="Too many"):
        create_contact_sheet([img1, img2], output)


def test_create_sprite_total_pixel_budget_exceeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("pixopt.sprite.MAX_SPRITE_TOTAL_PIXELS", 10)
    img1 = _make_tmp_image(tmp_path / "img1.png", (255, 0, 0))
    img2 = _make_tmp_image(tmp_path / "img2.png", (0, 255, 0))
    output = tmp_path / "sprite.png"

    result = create_sprite([img1, img2], output)
    assert not result.success
    assert "pixel budget" in (result.error or "").lower()


def test_create_contact_sheet_total_pixel_budget_exceeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("pixopt.sprite.MAX_SPRITE_TOTAL_PIXELS", 10)
    img1 = _make_tmp_image(tmp_path / "img1.png", (255, 0, 0))
    img2 = _make_tmp_image(tmp_path / "img2.png", (0, 255, 0))
    output = tmp_path / "contact.png"

    result = create_contact_sheet([img1, img2], output, cell_width=40, cell_height=40)
    assert not result.success
    assert "pixel budget" in (result.error or "").lower()


def test_create_contact_sheet_sheet_too_large(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("pixopt.sprite.MAX_IMAGE_DIMENSION", 50)
    img1 = _make_tmp_image(tmp_path / "img1.png", (255, 0, 0))
    img2 = _make_tmp_image(tmp_path / "img2.png", (0, 255, 0))
    output = tmp_path / "contact.png"

    result = create_contact_sheet([img1, img2], output, cell_width=40, cell_height=40)

    assert not result.success
    assert result.error is not None
    assert "too large" in result.error or "dimensions" in result.error


def test_create_sprite_source_parent_reference_rejected(tmp_path: Path) -> None:
    img = _make_tmp_image(tmp_path / "img.png")
    output = tmp_path / "sprite.png"
    source_with_parent = img.parent / ".." / img.name

    with pytest.raises(ValueError, match="parent"):
        create_sprite([source_with_parent], output)
