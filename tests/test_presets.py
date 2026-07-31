"""Tests for presets / profiles feature."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli import app
from pixopt.cli.preset_helpers import merge_preset
from pixopt.presets import (
    apply_preset,
    get_preset_names,
    load_custom_presets,
    resolve_preset,
)


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_builtin_preset_names() -> None:
    names = get_preset_names()
    assert "web" in names
    assert "social" in names
    assert "thumbnail" in names
    assert "e-commerce" in names
    assert "print" in names


def test_resolve_preset_returns_copy() -> None:
    p1 = resolve_preset("web")
    p2 = resolve_preset("web")
    assert p1 == p2
    p1["quality"] = 999
    assert resolve_preset("web")["quality"] == 80


def test_resolve_preset_unknown_raises() -> None:
    with pytest.raises(KeyError, match="Unknown preset"):
        resolve_preset("nonexistent")


def test_apply_preset_with_overrides() -> None:
    p = apply_preset("web", quality=50)
    assert p["quality"] == 50
    assert p["strip"] is True  # from preset


# ---------------------------------------------------------------------------
# Custom presets
# ---------------------------------------------------------------------------


def test_load_custom_presets(tmp_path: Path) -> None:
    f = tmp_path / "presets.json"
    f.write_text(json.dumps({"my-preset": {"quality": 75, "strip": False}}))
    custom = load_custom_presets(f)
    assert "my-preset" in custom
    assert custom["my-preset"]["quality"] == 75


def test_load_custom_presets_invalid_json(tmp_path: Path) -> None:
    f = tmp_path / "bad.json"
    f.write_text("{not valid json")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_custom_presets(f)


def test_load_custom_presets_invalid_keys(tmp_path: Path) -> None:
    f = tmp_path / "bad_keys.json"
    f.write_text(json.dumps({"bad": {"unknown-key": 1}}))
    with pytest.raises(ValueError, match="unknown keys"):
        load_custom_presets(f)


def test_load_custom_presets_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_custom_presets("nonexistent.json")


def test_load_custom_presets_too_large(tmp_path: Path) -> None:
    from pixopt._units import MAX_PRESET_FILE_SIZE_BYTES

    preset_file = tmp_path / "huge.json"
    preset_file.write_bytes(b"{" + b" " * (MAX_PRESET_FILE_SIZE_BYTES + 1) + b"}")
    with pytest.raises(ValueError, match="too large"):
        load_custom_presets(preset_file)


def test_load_custom_presets_invalid_quality(tmp_path: Path) -> None:
    f = tmp_path / "bad_quality.json"
    f.write_text(json.dumps({"bad": {"quality": 999}}))
    with pytest.raises(ValueError, match="quality"):
        load_custom_presets(f)


def test_load_custom_presets_invalid_max_width(tmp_path: Path) -> None:
    f = tmp_path / "bad_width.json"
    f.write_text(json.dumps({"bad": {"max-width": 0}}))
    with pytest.raises(ValueError, match="max-width"):
        load_custom_presets(f)


def test_load_custom_presets_non_boolean_flag(tmp_path: Path) -> None:
    f = tmp_path / "bad_bool.json"
    f.write_text(json.dumps({"bad": {"strip": "yes"}}))
    with pytest.raises(ValueError, match="strip"):
        load_custom_presets(f)


def test_custom_preset_overrides_builtin() -> None:
    custom = {"web": {"quality": 99}}
    p = resolve_preset("web", custom)
    assert p["quality"] == 99


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def _make_source(
    output_dir: Path, name: str = "source.jpg", size: tuple[int, int] = (800, 600)
) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (100, 150, 200)).save(path, "JPEG", quality=95)
    return path


def test_cli_optimize_with_preset_web(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    output = output_dir / "preset_web.jpg"
    result = runner.invoke(
        app,
        ["optimize", str(source), str(output), "--preset", "web"],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()
    with Image.open(output) as img:
        assert img.size[0] <= 1920
        assert img.size[1] <= 1080


def test_cli_optimize_with_preset_thumbnail(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    output = output_dir / "preset_thumb.jpg"
    result = runner.invoke(
        app,
        ["optimize", str(source), str(output), "--preset", "thumbnail"],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()
    with Image.open(output) as img:
        assert img.size[0] <= 300
        assert img.size[1] <= 300


def test_cli_optimize_preset_explicit_override(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    output = output_dir / "preset_override.jpg"
    result = runner.invoke(
        app,
        [
            "optimize",
            str(source),
            str(output),
            "--preset",
            "web",
            "--quality",
            "50",
        ],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()


def test_cli_optimize_with_preset_file(output_dir: Path, tmp_path: Path) -> None:
    preset_file = tmp_path / "custom.json"
    preset_file.write_text(
        json.dumps({"custom-web": {"quality": 60, "max-width": 400, "strip": True}})
    )
    runner = CliRunner()
    source = _make_source(output_dir)
    output = output_dir / "preset_custom.jpg"
    result = runner.invoke(
        app,
        [
            "optimize",
            str(source),
            str(output),
            "--preset",
            "custom-web",
            "--preset-file",
            str(preset_file),
        ],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()
    with Image.open(output) as img:
        assert img.size[0] <= 400


def test_cli_convert_with_preset_social(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    output = output_dir / "preset_social.jpg"
    result = runner.invoke(
        app,
        ["convert", str(source), str(output), "--preset", "social"],
    )
    assert result.exit_code == 0, result.output
    assert output.exists()
    with Image.open(output) as img:
        # social preset uses 1:1 aspect ratio, 1200x1200
        assert img.size[0] == img.size[1]


def test_cli_optimize_unknown_preset_errors(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_source(output_dir)
    output = output_dir / "preset_unknown.jpg"
    result = runner.invoke(
        app,
        ["optimize", str(source), str(output), "--preset", "nonexistent"],
    )
    assert result.exit_code != 0


def test_merge_preset_auto_orient_explicit_wins(tmp_path: Path) -> None:
    """Explicit --auto-orient must override a preset that disables it."""
    preset_file = tmp_path / "no-orient.json"
    preset_file.write_text(json.dumps({"no-orient": {"auto-orient": False}}))
    result = merge_preset("no-orient", str(preset_file), {"auto-orient": True})
    assert result["auto-orient"] is True
