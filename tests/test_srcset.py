"""Tests for responsive srcset generation."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from pixopt._units import MAX_IMAGE_DIMENSION
from pixopt.srcset_generator import generate_srcset_images


def _make_source(path: Path) -> Path:
    Image.new("RGB", (500, 500), (100, 150, 200)).save(path)
    return path


def test_generate_srcset_images_output_dir_parent_reference_rejected(tmp_path: Path) -> None:
    source = _make_source(tmp_path / "source.jpg")
    output_dir = tmp_path / "out" / ".."

    with pytest.raises(ValueError, match="parent"):
        generate_srcset_images(source, output_dir, widths=[100])


def test_generate_srcset_images_too_many_widths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("pixopt.srcset_generator.MAX_SRCSET_WIDTHS", 2)
    source = _make_source(tmp_path / "source.jpg")
    output_dir = tmp_path / "out"

    with pytest.raises(ValueError, match="Too many"):
        generate_srcset_images(source, output_dir, widths=[100, 200, 300])


def test_generate_srcset_images_width_too_large(tmp_path: Path) -> None:
    source = _make_source(tmp_path / "source.jpg")
    output_dir = tmp_path / "out"

    with pytest.raises(ValueError, match="width must be between"):
        generate_srcset_images(source, output_dir, widths=[MAX_IMAGE_DIMENSION + 1])


def test_generate_srcset_images_source_parent_reference_rejected(tmp_path: Path) -> None:
    source = _make_source(tmp_path / "source.jpg")
    bad_source = source.parent / ".." / source.name
    output_dir = tmp_path / "out"

    with pytest.raises(ValueError, match="parent"):
        generate_srcset_images(bad_source, output_dir, widths=[100])
