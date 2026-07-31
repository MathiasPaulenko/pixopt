"""Tests for the Pipeline builder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from pixopt.pipeline import Pipeline, PipelineResult


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_source(
    output_dir: Path, name: str = "source.jpg", size: tuple[int, int] = (800, 600)
) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (100, 150, 200)).save(path, "JPEG", quality=95)
    return path


def _make_watermark(
    output_dir: Path, name: str = "wm.png", size: tuple[int, int] = (100, 100)
) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, (255, 255, 255, 128)).save(path, "PNG")
    return path


# ---------------------------------------------------------------------------
# Basic pipeline tests
# ---------------------------------------------------------------------------


def test_pipeline_open_and_save(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "basic_out.webp"
    result = Pipeline().open(source).save(output).run()

    assert isinstance(result, PipelineResult)
    assert result.output_path == output
    assert result.output_path.exists()
    assert result.format == "WEBP"
    assert result.width == 800
    assert result.height == 600
    assert result.size_bytes > 0
    assert "open" in result.steps_executed[0]


def test_pipeline_resize(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "resized_out.webp"
    result = Pipeline().open(source).resize(max_width=400).save(output).run()

    assert result.width <= 400
    assert "resize" in result.steps_executed[1]


def test_pipeline_convert_mode(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "converted_out.webp"
    result = Pipeline().open(source).convert("RGBA").save(output).run()

    assert "convert" in result.steps_executed[1]


def test_pipeline_optimize_quality(output_dir: Path) -> None:
    source = _make_source(output_dir, "quality_src.jpg", (800, 600))
    # Add gradient variation for meaningful quality differences.
    img = Image.open(source)
    pixels = img.load()
    assert pixels is not None
    for y in range(img.height):
        for x in range(img.width):
            pixels[x, y] = (
                (x * 255) // img.width,
                (y * 255) // img.height,
                128,
            )
    img.save(source, "JPEG", quality=95)

    output_low = output_dir / "low_q.webp"
    output_high = output_dir / "high_q.webp"

    result_low = (
        Pipeline().open(source).optimize(quality=20, output_format="webp").save(output_low).run()
    )
    result_high = (
        Pipeline().open(source).optimize(quality=95, output_format="webp").save(output_high).run()
    )

    assert result_low.size_bytes < result_high.size_bytes


def test_pipeline_auto_orient(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "oriented_out.webp"
    result = Pipeline().open(source).auto_orient().save(output).run()

    assert "auto_orient" in result.steps_executed


def test_pipeline_watermark_text(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "wm_text_out.webp"
    result = (
        Pipeline()
        .open(source)
        .watermark_text("© Test", position="bottom-right", opacity=0.7)
        .save(output)
        .run()
    )

    assert result.output_path.exists()
    assert "watermark_text" in result.steps_executed[1]


def test_pipeline_watermark_image(output_dir: Path) -> None:
    source = _make_source(output_dir)
    wm = _make_watermark(output_dir)
    output = output_dir / "wm_img_out.webp"
    result = (
        Pipeline()
        .open(source)
        .watermark_image(wm, position="bottom-right", opacity=0.5, scale=0.2)
        .save(output)
        .run()
    )

    assert result.output_path.exists()
    assert "watermark_image" in result.steps_executed[1]


# ---------------------------------------------------------------------------
# Chained pipeline tests
# ---------------------------------------------------------------------------


def test_pipeline_full_chain(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "full_chain.webp"
    result = (
        Pipeline()
        .open(source)
        .auto_orient()
        .resize(max_width=400)
        .convert("RGB")
        .watermark_text("Pipeline", position="bottom-right")
        .optimize(quality=80, output_format="webp")
        .save(output)
        .run()
    )

    assert result.output_path.exists()
    assert result.format == "WEBP"
    assert result.width <= 400
    assert len(result.steps_executed) >= 5
    assert any("watermark_text" in s for s in result.steps_executed)
    assert any("optimize" in s for s in result.steps_executed)


def test_pipeline_multiple_resizes(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "multi_resize.webp"
    result = Pipeline().open(source).resize(max_width=600).resize(max_width=300).save(output).run()

    assert result.width <= 300


def test_pipeline_resize_then_watermark_then_optimize(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "rwm_opt.webp"
    result = (
        Pipeline()
        .open(source)
        .resize(max_width=400)
        .watermark_text("Hi", font_size=24)
        .optimize(quality=70)
        .save(output)
        .run()
    )

    assert result.output_path.exists()
    assert result.size_bytes > 0


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


def test_pipeline_no_source_raises() -> None:
    with pytest.raises(ValueError, match="No source"):
        Pipeline().run()


def test_pipeline_nonexistent_source_raises(output_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Pipeline().open("nonexistent.jpg").save(output_dir / "out.webp").run()


def test_pipeline_no_output_uses_default(output_dir: Path) -> None:
    source = _make_source(output_dir, "default_src.jpg")
    result = Pipeline().open(source).optimize(quality=85).run()
    assert result.output_path.exists()
    # Default output should be source with .webp extension
    assert result.output_path.suffix == ".webp"


# ---------------------------------------------------------------------------
# Introspection tests
# ---------------------------------------------------------------------------


def test_pipeline_steps_property(output_dir: Path) -> None:
    source = _make_source(output_dir)
    p = Pipeline().open(source).resize(max_width=400).watermark_text("Test").optimize(quality=85)
    steps = p.steps
    assert len(steps) == 4
    assert "open" in steps[0]
    assert "resize" in steps[1]
    assert "watermark_text" in steps[2]
    assert "optimize" in steps[3]


def test_pipeline_result_to_dict(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "dict_out.webp"
    result = Pipeline().open(source).resize(max_width=400).save(output).run()
    d = result.to_dict()
    assert isinstance(d, dict)
    assert isinstance(d["output_path"], str)
    assert isinstance(d["steps_executed"], list)
    json.dumps(d)


# ---------------------------------------------------------------------------
# Output format tests
# ---------------------------------------------------------------------------


def test_pipeline_output_jpeg(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "jpeg_out.jpg"
    result = Pipeline().open(source).optimize(quality=85, output_format="jpeg").save(output).run()

    assert result.format == "JPEG"
    assert result.output_path.suffix == ".jpg"


def test_pipeline_output_png(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "png_out.png"
    result = Pipeline().open(source).optimize(quality=90, output_format="png").save(output).run()

    assert result.format == "PNG"


def test_pipeline_auto_ext_from_format(output_dir: Path) -> None:
    source = _make_source(output_dir)
    output = output_dir / "auto_ext"
    result = Pipeline().open(source).optimize(quality=85, output_format="webp").save(output).run()

    assert result.output_path.suffix == ".webp"


def test_pipeline_source_parent_reference_rejected(tmp_path: Path) -> None:
    parent_source = tmp_path.parent / "src.jpg"
    Image.new("RGB", (100, 100)).save(parent_source)
    bad_source = tmp_path / ".." / "src.jpg"
    output = tmp_path / "out.webp"

    with pytest.raises(ValueError, match="parent"):
        Pipeline().open(bad_source).save(output).run()
