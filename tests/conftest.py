"""pytest configuration: keep bytecode out of the source tree."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.dont_write_bytecode = True


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """Create a simple red test image."""
    img_path = tmp_path / "test.jpg"
    Image.new("RGB", (800, 600), color=(255, 0, 0)).save(img_path, quality=95)
    return img_path


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    """Create a directory with a JPEG and a PNG."""
    d = tmp_path / "images"
    d.mkdir()
    Image.new("RGB", (200, 200), color=(255, 0, 0)).save(d / "a.jpg")
    Image.new("RGB", (200, 200), color=(0, 255, 0)).save(d / "b.png")
    return d
