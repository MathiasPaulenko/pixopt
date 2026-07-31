"""Tests for next-generation format support (JXL, WebP 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli.app import app
from pixopt.nextgen import (
    ConversionResult,
    FormatSupport,
    FormatSupportInfo,
    NextGenFormat,
    convert_to_nextgen,
    detect_format_support,
    is_format_supported,
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
    size: tuple[int, int] = (200, 200),
    color: tuple[int, int, int] = (100, 150, 200),
    fmt: str = "PNG",
) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, fmt)
    return path


# ---------------------------------------------------------------------------
# detect_format_support tests
# ---------------------------------------------------------------------------


def test_detect_format_support_returns_format_support() -> None:
    support = detect_format_support()
    assert isinstance(support, FormatSupport)


def test_detect_format_support_has_jxl_and_webp2() -> None:
    support = detect_format_support()
    format_names = [f.format for f in support.formats]
    assert "jxl" in format_names
    assert "webp2" in format_names


def test_detect_format_support_jxl_info() -> None:
    support = detect_format_support()
    jxl = support.get("jxl")
    assert jxl is not None
    assert isinstance(jxl, FormatSupportInfo)
    assert jxl.format == "jxl"
    # supported is a bool (True or False depending on environment)
    assert isinstance(jxl.supported, bool)


def test_detect_format_support_webp2_info() -> None:
    support = detect_format_support()
    webp2 = support.get("webp2")
    assert webp2 is not None
    assert isinstance(webp2, FormatSupportInfo)
    assert webp2.format == "webp2"
    assert isinstance(webp2.supported, bool)


def test_detect_format_support_to_dict_serializable() -> None:
    support = detect_format_support()
    d = support.to_dict()
    json.dumps(d)
    assert "formats" in d
    assert len(d["formats"]) == 2


def test_detect_format_support_get_unknown_returns_none() -> None:
    support = detect_format_support()
    assert support.get("unknown") is None


def test_detect_format_support_any_supported() -> None:
    support = detect_format_support()
    # any_supported is a bool
    assert isinstance(support.any_supported, bool)


def test_format_support_info_to_dict() -> None:
    info = FormatSupportInfo(format="jxl", supported=True, plugin="test")
    d = info.to_dict()
    assert d["format"] == "jxl"
    assert d["supported"] is True
    assert d["plugin"] == "test"
    json.dumps(d)


# ---------------------------------------------------------------------------
# is_format_supported tests
# ---------------------------------------------------------------------------


def test_is_format_supported_jxl_returns_bool() -> None:
    result = is_format_supported("jxl")
    assert isinstance(result, bool)


def test_is_format_supported_webp2_returns_bool() -> None:
    result = is_format_supported("webp2")
    assert isinstance(result, bool)


def test_is_format_supported_with_enum() -> None:
    result = is_format_supported(NextGenFormat.JXL)
    assert isinstance(result, bool)


def test_is_format_supported_unknown_format() -> None:
    result = is_format_supported("unknown")
    assert result is False


# ---------------------------------------------------------------------------
# NextGenFormat enum tests
# ---------------------------------------------------------------------------


def test_nextgen_format_values() -> None:
    assert NextGenFormat.JXL.value == "jxl"
    assert NextGenFormat.WEBP2.value == "webp2"


# ---------------------------------------------------------------------------
# convert_to_nextgen tests
# ---------------------------------------------------------------------------


def test_convert_to_nextgen_fallback_to_webp(output_dir: Path) -> None:
    """When JXL is not supported, should fall back to WEBP."""
    img = _make_image(output_dir, "source.png", (200, 200))
    out = output_dir / "output.jxl"

    result = convert_to_nextgen(img, out, fmt="jxl", fallback=True, fallback_format="webp")

    assert isinstance(result, ConversionResult)
    assert result.success

    if not result.supported:
        # Fallback occurred
        assert result.fallback is True
        assert result.fallback_format == "webp"
        assert result.output.suffix == ".webp"
        assert result.output.exists()
    else:
        # JXL was actually supported
        assert result.fallback is False
        assert result.output.exists()


def test_convert_to_nextgen_no_fallback_unsupported(output_dir: Path) -> None:
    """When format is not supported and fallback is disabled, should fail gracefully."""
    img = _make_image(output_dir, "source_nf.png")
    out = output_dir / "output_nf.jxl"

    result = convert_to_nextgen(img, out, fmt="jxl", fallback=False)

    if not is_format_supported("jxl"):
        assert not result.success
        assert result.error is not None
        assert "not supported" in result.error
    else:
        assert result.success


def test_convert_to_nextgen_nonexistent_source_raises(output_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        convert_to_nextgen(output_dir / "nope.png", output_dir / "out.jxl")


def test_convert_to_nextgen_rejects_parent_reference_source(output_dir: Path) -> None:
    with pytest.raises(ValueError, match="parent"):
        convert_to_nextgen(output_dir / ".." / "outside.png", output_dir / "out.jxl")


def test_convert_to_nextgen_creates_parent_dir(output_dir: Path) -> None:
    img = _make_image(output_dir, "parent.png")
    out = output_dir / "subdir" / "nested" / "output.jxl"

    result = convert_to_nextgen(img, out, fmt="jxl", fallback=True)

    assert result.success
    assert result.output.parent.exists()


def test_convert_to_nextgen_with_enum_format(output_dir: Path) -> None:
    img = _make_image(output_dir, "enum.png")
    out = output_dir / "enum_out.jxl"

    result = convert_to_nextgen(img, out, fmt=NextGenFormat.JXL, fallback=True)

    assert result.success


def test_convert_to_nextgen_to_dict_serializable(output_dir: Path) -> None:
    img = _make_image(output_dir, "dict.png")
    out = output_dir / "dict_out.jxl"

    result = convert_to_nextgen(img, out, fmt="jxl", fallback=True)

    d = result.to_dict()
    json.dumps(d)
    assert d["success"] is True


def test_convert_to_nextgen_webp2_fallback(output_dir: Path) -> None:
    img = _make_image(output_dir, "webp2_src.png")
    out = output_dir / "webp2_out.webp2"

    result = convert_to_nextgen(img, out, fmt="webp2", fallback=True, fallback_format="webp")

    assert result.success
    if not result.supported:
        assert result.fallback is True
        assert result.output.exists()


def test_convert_to_nextgen_quality_param(output_dir: Path) -> None:
    img = _make_image(output_dir, "quality.png")
    out = output_dir / "quality_out.jxl"

    result = convert_to_nextgen(img, out, fmt="jxl", quality=50, fallback=True)

    assert result.success


def test_convert_to_nextgen_savings_calculated(output_dir: Path) -> None:
    img = _make_image(output_dir, "savings.png", (500, 500))
    out = output_dir / "savings_out.jxl"

    result = convert_to_nextgen(img, out, fmt="jxl", fallback=True)

    assert result.success
    assert result.original_size > 0
    assert result.output_size > 0
    # savings_bytes = original - output
    assert result.savings_bytes == result.original_size - result.output_size


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_nextgen_detect() -> None:
    result = runner.invoke(app, ["nextgen", "detect"])

    assert result.exit_code == 0
    assert "JXL" in result.output
    assert "WEBP2" in result.output


def test_cli_nextgen_detect_json() -> None:
    result = runner.invoke(app, ["nextgen", "detect", "--json"])

    assert result.exit_code == 0
    parsed = json.loads(result.stdout.strip())
    assert "formats" in parsed
    assert len(parsed["formats"]) == 2


def test_cli_nextgen_convert_fallback(output_dir: Path) -> None:
    img = _make_image(output_dir, "cli_convert.png")
    out = output_dir / "cli_out.jxl"

    result = runner.invoke(app, ["nextgen", "convert", str(img), "-o", str(out), "-f", "jxl"])

    assert result.exit_code == 0
    # Output should exist (either as .jxl or .webp fallback)
    assert out.exists() or out.with_suffix(".webp").exists()


def test_cli_nextgen_convert_json(output_dir: Path) -> None:
    img = _make_image(output_dir, "cli_json.png")
    out = output_dir / "cli_json_out.jxl"

    result = runner.invoke(
        app, ["nextgen", "convert", str(img), "-o", str(out), "-f", "jxl", "--json"]
    )

    assert result.exit_code == 0
    parsed = json.loads(result.stdout.strip())
    assert parsed["success"] is True


def test_cli_nextgen_convert_no_fallback(output_dir: Path) -> None:
    img = _make_image(output_dir, "cli_nf.png")
    out = output_dir / "cli_nf_out.jxl"

    result = runner.invoke(
        app,
        ["nextgen", "convert", str(img), "-o", str(out), "-f", "jxl", "--no-fallback"],
    )

    if not is_format_supported("jxl"):
        assert result.exit_code == 1
    else:
        assert result.exit_code == 0


def test_cli_nextgen_unknown_action() -> None:
    result = runner.invoke(app, ["nextgen", "unknown"])

    assert result.exit_code != 0
