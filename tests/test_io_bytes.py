"""Tests for bytes and base64 I/O."""

from __future__ import annotations

import base64 as b64
import io
import json
from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError

from pixopt.io_bytes import (
    BytesResult,
    base64_to_image,
    bytes_to_image,
    image_to_base64,
    image_to_bytes,
    optimize_base64,
    optimize_bytes,
)
from pixopt.models import OutputFormat


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_image_bytes(
    size: tuple[int, int] = (200, 200),
    color: tuple[int, int, int] = (100, 150, 200),
    fmt: str = "JPEG",
    quality: int = 90,
) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, fmt, quality=quality)
    return buf.getvalue()


def _make_gradient_bytes(size: tuple[int, int] = (200, 200), fmt: str = "JPEG") -> bytes:
    img = Image.new("RGB", size)
    pixels = img.load()
    assert pixels is not None
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = ((x * 255) // size[0], (y * 255) // size[1], 128)
    buf = io.BytesIO()
    img.save(buf, fmt, quality=95)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# bytes_to_image / image_to_bytes
# ---------------------------------------------------------------------------


def test_bytes_to_image_returns_pil_image() -> None:
    data = _make_image_bytes()
    img = bytes_to_image(data)
    assert isinstance(img, Image.Image)
    assert img.size == (200, 200)


def test_bytes_to_image_invalid_bytes_raises() -> None:
    with pytest.raises(UnidentifiedImageError):
        bytes_to_image(b"not an image")


def test_image_to_bytes_returns_bytes() -> None:
    img = Image.new("RGB", (100, 100), (200, 100, 50))
    data = image_to_bytes(img, fmt="WEBP")
    assert isinstance(data, bytes)
    assert len(data) > 0

    # Should be a valid WEBP
    decoded = Image.open(io.BytesIO(data))
    assert decoded.format == "WEBP"


def test_image_to_bytes_jpeg() -> None:
    img = Image.new("RGB", (100, 100), (200, 100, 50))
    data = image_to_bytes(img, fmt="JPEG")
    decoded = Image.open(io.BytesIO(data))
    assert decoded.format == "JPEG"


def test_image_to_bytes_png() -> None:
    img = Image.new("RGBA", (100, 100), (200, 100, 50, 255))
    data = image_to_bytes(img, fmt="PNG")
    decoded = Image.open(io.BytesIO(data))
    assert decoded.format == "PNG"


def test_image_to_bytes_roundtrip() -> None:
    img = Image.new("RGB", (100, 100), (200, 100, 50))
    data = image_to_bytes(img, fmt="PNG")
    img2 = bytes_to_image(data)
    img2.load()
    assert img2.size == (100, 100)


# ---------------------------------------------------------------------------
# image_to_base64 / base64_to_image
# ---------------------------------------------------------------------------


def test_image_to_base64_returns_string() -> None:
    img = Image.new("RGB", (100, 100), (200, 100, 50))
    b64_str = image_to_base64(img, fmt="WEBP")
    assert isinstance(b64_str, str)
    # Should be valid base64
    decoded = b64.b64decode(b64_str)
    assert len(decoded) > 0


def test_base64_to_image_returns_pil_image() -> None:
    img = Image.new("RGB", (100, 100), (200, 100, 50))
    b64_str = image_to_base64(img, fmt="PNG")
    img2 = base64_to_image(b64_str)
    assert isinstance(img2, Image.Image)
    assert img2.size == (100, 100)


def test_base64_roundtrip() -> None:
    img = Image.new("RGB", (100, 100), (200, 100, 50))
    b64_str = image_to_base64(img, fmt="JPEG")
    img2 = base64_to_image(b64_str)
    img2.load()
    assert img2.size == (100, 100)


def test_base64_to_image_invalid_raises() -> None:
    with pytest.raises(ValueError, match="Invalid base64"):
        base64_to_image("not valid base64 image data")


# ---------------------------------------------------------------------------
# optimize_bytes
# ---------------------------------------------------------------------------


def test_optimize_bytes_returns_bytes_result() -> None:
    data = _make_image_bytes(size=(800, 600), quality=95)
    result = optimize_bytes(data, output_format=OutputFormat.WEBP, quality=85)

    assert isinstance(result, BytesResult)
    assert result.success
    assert result.format == "WEBP"
    assert result.width == 800
    assert result.height == 600
    assert len(result.data) > 0
    assert result.optimized_size == len(result.data)


def test_optimize_bytes_reduces_size() -> None:
    data = _make_gradient_bytes(size=(800, 600), fmt="JPEG")
    result = optimize_bytes(data, output_format=OutputFormat.WEBP, quality=50)

    assert result.success
    assert result.optimized_size < result.original_size
    assert result.savings_bytes > 0
    assert result.savings_percent > 0


def test_optimize_bytes_resize() -> None:
    data = _make_image_bytes(size=(800, 600))
    result = optimize_bytes(data, max_width=400, output_format=OutputFormat.WEBP)

    assert result.success
    assert result.width == 400
    assert result.height == 300


def test_optimize_bytes_format_jpeg() -> None:
    data = _make_image_bytes(size=(200, 200))
    result = optimize_bytes(data, output_format=OutputFormat.JPEG, quality=85)

    assert result.success
    assert result.format == "JPEG"


def test_optimize_bytes_format_png() -> None:
    data = _make_image_bytes(size=(200, 200))
    result = optimize_bytes(data, output_format=OutputFormat.PNG)

    assert result.success
    assert result.format == "PNG"


def test_optimize_bytes_auto_format() -> None:
    data = _make_image_bytes(size=(200, 200), fmt="PNG")
    result = optimize_bytes(data, output_format=OutputFormat.AUTO)

    assert result.success
    # AUTO should keep the original format (PNG)
    assert result.format == "PNG"


def test_optimize_bytes_original_format() -> None:
    data = _make_image_bytes(size=(200, 200), fmt="JPEG")
    result = optimize_bytes(data, output_format=OutputFormat.ORIGINAL)

    assert result.success
    assert result.format == "JPEG"


def test_optimize_bytes_invalid_data() -> None:
    result = optimize_bytes(b"not an image")

    assert not result.success
    assert result.error is not None
    assert result.data == b""


def test_optimize_bytes_invalid_format() -> None:
    data = _make_image_bytes()
    result = optimize_bytes(data, output_format="INVALID")

    assert not result.success
    assert result.error is not None


def test_optimize_bytes_strip_metadata() -> None:
    # Create an image with EXIF data
    img = Image.new("RGB", (200, 200), (100, 100, 100))
    buf = io.BytesIO()
    img.save(
        buf,
        "JPEG",
        quality=95,
        exif=b"Exif\x00\x00II*\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
    )
    data = buf.getvalue()

    result = optimize_bytes(data, output_format=OutputFormat.JPEG, strip_metadata=True)
    assert result.success
    # The optimized image should not have the custom EXIF
    decoded = Image.open(io.BytesIO(result.data))
    assert decoded.getexif() == {}


def test_optimize_bytes_lossless() -> None:
    data = _make_image_bytes(size=(200, 200), fmt="PNG")
    result = optimize_bytes(data, output_format=OutputFormat.WEBP, lossless=True)

    assert result.success
    assert result.format == "WEBP"


def test_optimize_bytes_to_dict_serializable() -> None:
    data = _make_image_bytes()
    result = optimize_bytes(data, output_format=OutputFormat.WEBP)
    d = result.to_dict()
    json.dumps(d)
    assert d["success"] is True
    assert "data" not in d  # data is bytes, not in dict


def test_optimize_bytes_human_sizes() -> None:
    data = _make_image_bytes(size=(800, 600), quality=95)
    result = optimize_bytes(data, output_format=OutputFormat.WEBP, quality=50)

    assert "B" in result.human_original_size or "KB" in result.human_original_size
    assert "B" in result.human_optimized_size or "KB" in result.human_optimized_size


# ---------------------------------------------------------------------------
# optimize_base64
# ---------------------------------------------------------------------------


def test_optimize_base64_returns_result() -> None:
    from pixopt.io_bytes import Base64Result

    data = _make_image_bytes(size=(200, 200))
    b64_str = b64.b64encode(data).decode("ascii")
    result = optimize_base64(b64_str, output_format=OutputFormat.WEBP, quality=85)

    assert isinstance(result, Base64Result)
    assert result.success is True
    assert result.base64 is not None
    assert isinstance(result.base64, str)
    assert result.format == "WEBP"


def test_optimize_base64_roundtrip() -> None:
    data = _make_image_bytes(size=(200, 200))
    b64_str = b64.b64encode(data).decode("ascii")
    result = optimize_base64(b64_str, output_format=OutputFormat.PNG)

    assert result.success
    assert result.base64 is not None
    decoded = base64_to_image(result.base64)
    decoded.load()
    assert decoded.size == (200, 200)
    assert decoded.format == "PNG"


def test_optimize_base64_invalid_data() -> None:
    result = optimize_base64("not valid image data")

    assert not result.success
    assert result.base64 is None
    assert result.error is not None


def test_optimize_base64_invalid_base64_chars() -> None:
    result = optimize_base64("not-base64!!!")

    assert not result.success
    assert result.base64 is None
    assert "Invalid base64" in (result.error or "")


def test_optimize_base64_resize() -> None:
    data = _make_image_bytes(size=(800, 600))
    b64_str = b64.b64encode(data).decode("ascii")
    result = optimize_base64(b64_str, max_width=400, output_format=OutputFormat.WEBP)

    assert result.success
    assert result.width == 400
    assert result.height == 300


def test_optimize_base64_json_serializable() -> None:
    data = _make_image_bytes(size=(200, 200))
    b64_str = b64.b64encode(data).decode("ascii")
    result = optimize_base64(b64_str, output_format=OutputFormat.WEBP)

    json.dumps(result.to_dict())


def test_optimize_base64_reduces_size() -> None:
    data = _make_gradient_bytes(size=(800, 600), fmt="JPEG")
    b64_str = b64.b64encode(data).decode("ascii")
    result = optimize_base64(b64_str, output_format=OutputFormat.WEBP, quality=50)

    assert result.success
    assert result.optimized_size < result.original_size


def test_optimize_bytes_dimension_too_large() -> None:
    from pixopt._units import MAX_IMAGE_DIMENSION

    img = Image.new("RGB", (MAX_IMAGE_DIMENSION + 1, 100), color=(0, 128, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    result = optimize_bytes(buf.getvalue())
    assert result.success is False
    assert "too large" in (result.error or "").lower()


def test_optimize_bytes_input_too_large(monkeypatch) -> None:
    monkeypatch.setattr("pixopt.io_bytes.MAX_INPUT_BYTES", 10)
    result = optimize_bytes(b"a" * 11)
    assert not result.success
    assert "too large" in (result.error or "").lower()


def test_base64_to_image_too_long(monkeypatch) -> None:
    monkeypatch.setattr("pixopt.io_bytes.MAX_BASE64_LENGTH", 10)
    with pytest.raises(ValueError):
        base64_to_image("YWFhYWFhYWFhYQ==")


def test_base64_to_image_decoded_too_large(monkeypatch) -> None:
    monkeypatch.setattr("pixopt.io_bytes.MAX_INPUT_BYTES", 10)
    raw = b"\xff\xd8\xff\xe0" + b"\x00" * 16
    b64_str = b64.b64encode(raw).decode("ascii")
    with pytest.raises(ValueError, match="too large"):
        base64_to_image(b64_str)
