"""Tests for watermark and overlay feature."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli import app
from pixopt.watermark import (
    WatermarkPosition,
    WatermarkResult,
    add_image_watermark,
    add_text_watermark,
)


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_source(
    output_dir: Path, name: str = "source.jpg", size: tuple[int, int] = (400, 300)
) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (100, 150, 200)).save(path, "JPEG", quality=95)
    return path


def _make_logo(output_dir: Path, name: str = "logo.png", size: tuple[int, int] = (80, 40)) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", size, (255, 0, 0, 200))
    img.save(path, "PNG")
    return path


# ---------------------------------------------------------------------------
# add_text_watermark unit tests
# ---------------------------------------------------------------------------


def test_text_watermark_basic(output_dir: Path) -> None:
    source = _make_source(output_dir, "text_basic.jpg")
    output = output_dir / "text_basic_out.png"
    result = add_text_watermark(source, output, "© 2025")
    assert isinstance(result, WatermarkResult)
    assert result.watermark_type == "text"
    assert result.width == 400
    assert result.height == 300
    assert output.exists()


def test_text_watermark_positions(output_dir: Path) -> None:
    source = _make_source(output_dir, "text_pos.jpg")
    for pos in WatermarkPosition:
        output = output_dir / f"text_pos_{pos.value}.png"
        result = add_text_watermark(source, output, "WATERMARK", position=pos)
        assert result.watermark_type == "text"
        assert output.exists()


def test_text_watermark_opacity(output_dir: Path) -> None:
    source = _make_source(output_dir, "text_opacity.jpg")
    output = output_dir / "text_opacity_out.png"
    result = add_text_watermark(source, output, "TEST", opacity=0.8)
    assert result.watermark_type == "text"
    assert output.exists()


def test_text_watermark_padding(output_dir: Path) -> None:
    source = _make_source(output_dir, "text_pad.jpg")
    output = output_dir / "text_pad_out.png"
    result = add_text_watermark(source, output, "PAD", padding=50)
    assert result.watermark_type == "text"
    assert output.exists()


def test_text_watermark_font_size(output_dir: Path) -> None:
    source = _make_source(output_dir, "text_font.jpg")
    output = output_dir / "text_font_out.png"
    result = add_text_watermark(source, output, "BIG", font_size=72)
    assert result.watermark_type == "text"
    assert output.exists()


def test_text_watermark_color(output_dir: Path) -> None:
    source = _make_source(output_dir, "text_color.jpg")
    output = output_dir / "text_color_out.png"
    result = add_text_watermark(source, output, "COLOR", color=(255, 0, 0))
    assert result.watermark_type == "text"
    assert output.exists()


def test_text_watermark_to_dict_serializable(output_dir: Path) -> None:
    source = _make_source(output_dir, "text_dict.jpg")
    output = output_dir / "text_dict_out.png"
    result = add_text_watermark(source, output, "DICT")
    d = result.to_dict()
    assert isinstance(d, dict)
    assert isinstance(d["source_path"], str)
    assert isinstance(d["output_path"], str)
    json.dumps(d)


def test_text_watermark_file_not_found(output_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        add_text_watermark("nonexistent.jpg", output_dir / "out.png", "TEST")


# ---------------------------------------------------------------------------
# add_image_watermark unit tests
# ---------------------------------------------------------------------------


def test_image_watermark_basic(output_dir: Path) -> None:
    source = _make_source(output_dir, "img_basic.jpg")
    logo = _make_logo(output_dir, "img_basic_logo.png")
    output = output_dir / "img_basic_out.png"
    result = add_image_watermark(source, output, logo)
    assert isinstance(result, WatermarkResult)
    assert result.watermark_type == "image"
    assert result.width == 400
    assert result.height == 300
    assert output.exists()


def test_image_watermark_positions(output_dir: Path) -> None:
    source = _make_source(output_dir, "img_pos.jpg")
    logo = _make_logo(output_dir, "img_pos_logo.png")
    for pos in WatermarkPosition:
        output = output_dir / f"img_pos_{pos.value}.png"
        result = add_image_watermark(source, output, logo, position=pos)
        assert result.watermark_type == "image"
        assert output.exists()


def test_image_watermark_opacity(output_dir: Path) -> None:
    source = _make_source(output_dir, "img_opacity.jpg")
    logo = _make_logo(output_dir, "img_opacity_logo.png")
    output = output_dir / "img_opacity_out.png"
    result = add_image_watermark(source, output, logo, opacity=0.3)
    assert result.watermark_type == "image"
    assert output.exists()


def test_image_watermark_scale(output_dir: Path) -> None:
    source = _make_source(output_dir, "img_scale.jpg")
    logo = _make_logo(output_dir, "img_scale_logo.png", (200, 100))
    output = output_dir / "img_scale_out.png"
    result = add_image_watermark(source, output, logo, scale=0.1)
    assert result.watermark_type == "image"
    assert output.exists()


def test_image_watermark_padding(output_dir: Path) -> None:
    source = _make_source(output_dir, "img_pad.jpg")
    logo = _make_logo(output_dir, "img_pad_logo.png")
    output = output_dir / "img_pad_out.png"
    result = add_image_watermark(source, output, logo, padding=5)
    assert result.watermark_type == "image"
    assert output.exists()


def test_image_watermark_to_dict_serializable(output_dir: Path) -> None:
    source = _make_source(output_dir, "img_dict.jpg")
    logo = _make_logo(output_dir, "img_dict_logo.png")
    output = output_dir / "img_dict_out.png"
    result = add_image_watermark(source, output, logo)
    d = result.to_dict()
    assert isinstance(d, dict)
    json.dumps(d)


def test_image_watermark_file_not_found(output_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        add_image_watermark("nonexistent.jpg", output_dir / "out.png", "also_nonexistent.png")


# ---------------------------------------------------------------------------
# CLI watermark command tests
# ---------------------------------------------------------------------------


def test_cli_watermark_text(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir, "cli_text.jpg")
    output = output_dir / "cli_text_out.png"
    result = runner.invoke(
        app,
        ["watermark", str(source), str(output), "--text", "© Test", "--position", "bottom-right"],
    )
    assert result.exit_code == 0
    assert output.exists()
    assert "Watermark added" in result.output


def test_cli_watermark_text_json(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir, "cli_text_json.jpg")
    output = output_dir / "cli_text_json_out.png"
    result = runner.invoke(
        app,
        ["watermark", str(source), str(output), "--text", "JSON", "--output", "json"],
    )
    assert result.exit_code == 0
    assert '"watermark_type"' in result.output or "'watermark_type'" in result.output


def test_cli_watermark_image(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir, "cli_img.jpg")
    logo = _make_logo(output_dir, "cli_img_logo.png")
    output = output_dir / "cli_img_out.png"
    result = runner.invoke(
        app,
        [
            "watermark",
            str(source),
            str(output),
            "--watermark-image",
            str(logo),
            "--position",
            "center",
        ],
    )
    assert result.exit_code == 0
    assert output.exists()


def test_cli_watermark_no_text_or_image(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir, "cli_none.jpg")
    output = output_dir / "cli_none_out.png"
    result = runner.invoke(
        app,
        ["watermark", str(source), str(output)],
    )
    assert result.exit_code != 0
    assert "text" in result.output.lower() or "watermark-image" in result.output.lower()


def test_cli_watermark_nonexistent_file(output_dir: Path) -> None:
    runner = CliRunner()
    output = output_dir / "cli_nonexist_out.png"
    result = runner.invoke(
        app,
        ["watermark", "nonexistent.jpg", str(output), "--text", "TEST"],
    )
    assert result.exit_code != 0


def test_add_text_watermark_output_parent_reference_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    output = tmp_path / ".." / "out.png"
    with pytest.raises(ValueError, match="parent"):
        add_text_watermark(source, output, "X")


def test_add_image_watermark_output_parent_reference_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    watermark = tmp_path / "logo.png"
    Image.new("RGBA", (20, 20)).save(watermark)
    output = tmp_path / ".." / "out.png"
    with pytest.raises(ValueError, match="parent"):
        add_image_watermark(source, output, watermark)


def test_add_text_watermark_dimensions_too_large(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pixopt.watermark.MAX_IMAGE_DIMENSION", 50)
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="dimensions too large"):
        add_text_watermark(source, output, "X")


def test_add_image_watermark_dimensions_too_large(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("pixopt.watermark.MAX_IMAGE_DIMENSION", 50)
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    watermark = tmp_path / "logo.png"
    Image.new("RGBA", (20, 20)).save(watermark)
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="dimensions too large"):
        add_image_watermark(source, output, watermark)


def test_add_text_watermark_invalid_font_extension(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    font = tmp_path / "font.txt"
    font.write_text("not a font", encoding="utf-8")
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match=r"\.ttf or \.otf"):
        add_text_watermark(source, output, "X", font_path=font)


def test_add_text_watermark_font_file_too_large(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    font = tmp_path / "font.ttf"
    font.write_bytes(b"\x00" * (10 * 1024 * 1024 + 1))
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="font file too large"):
        add_text_watermark(source, output, "X", font_path=font)


def test_add_text_watermark_font_file_not_found(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    font = tmp_path / "missing.ttf"
    output = tmp_path / "out.png"
    with pytest.raises((OSError, FileNotFoundError)):
        add_text_watermark(source, output, "X", font_path=font)


def test_add_text_watermark_corrupt_font_file(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    font = tmp_path / "font.ttf"
    font.write_bytes(b"\xde\xad\xbe\xef" * 16)
    output = tmp_path / "out.png"
    with pytest.raises(OSError):
        add_text_watermark(source, output, "X", font_path=font)


def test_add_text_watermark_source_parent_reference_rejected(tmp_path: Path) -> None:
    source = tmp_path / ".." / "source.jpg"
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="parent"):
        add_text_watermark(source, output, "X")


def test_add_image_watermark_watermark_parent_reference_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    watermark = tmp_path / ".." / "logo.png"
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="parent"):
        add_image_watermark(source, output, watermark)


def test_add_text_watermark_font_parent_reference_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    font = tmp_path / ".." / "font.ttf"
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="parent"):
        add_text_watermark(source, output, "X", font_path=font)


def test_add_text_watermark_source_too_large(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("pixopt.image_ops.MAX_INPUT_BYTES", 5)
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="Input too large"):
        add_text_watermark(source, output, "X")


def test_add_text_watermark_invalid_padding(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="padding"):
        add_text_watermark(source, output, "X", padding=-1)


def test_add_text_watermark_font_size_too_large(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="font_size"):
        add_text_watermark(source, output, "X", font_size=1001)


def test_add_image_watermark_invalid_scale(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    watermark = tmp_path / "logo.png"
    Image.new("RGBA", (20, 20)).save(watermark)
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="scale"):
        add_image_watermark(source, output, watermark, scale=-0.5)


def test_add_image_watermark_invalid_padding(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    watermark = tmp_path / "logo.png"
    Image.new("RGBA", (20, 20)).save(watermark)
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="padding"):
        add_image_watermark(source, output, watermark, padding=-1)


def test_add_text_watermark_text_too_long(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="exceeds maximum length"):
        add_text_watermark(source, output, "x" * 1001)


def test_add_text_watermark_text_not_string(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    output = tmp_path / "out.png"
    with pytest.raises(ValueError, match="must be a string"):
        add_text_watermark(source, output, 123)  # type: ignore[arg-type]


def test_add_image_watermark_zero_width_watermark(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)
    watermark = tmp_path / "logo.png"
    Image.new("RGBA", (20, 20)).save(watermark)
    output = tmp_path / "out.png"
    # Guard against the (unlikely) case where a loaded watermark reports zero width.
    monkeypatch.setattr("PIL.Image.Image.width", property(lambda self: 0))
    with pytest.raises(ValueError, match="invalid dimensions"):
        add_image_watermark(source, output, watermark, scale=0.5)
