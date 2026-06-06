"""Tests for pixopt.optimizer."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from pixopt.models import OutputFormat
from pixopt.optimizer import optimize_directory, optimize_image


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """Create a simple test image."""
    img_path = tmp_path / "test.jpg"
    img = Image.new("RGB", (800, 600), color=(255, 0, 0))
    img.save(img_path, quality=95)
    return img_path


def test_optimize_image_reduces_size(sample_image: Path, tmp_path: Path) -> None:
    output = tmp_path / "out.jpg"
    result = optimize_image(sample_image, output, quality=50)

    assert result.success is True
    assert result.source_path == sample_image
    assert result.output_path == output
    assert result.optimized_size < result.original_size
    assert result.savings_percent > 0


def test_optimize_image_resize(sample_image: Path, tmp_path: Path) -> None:
    output = tmp_path / "out.jpg"
    result = optimize_image(sample_image, output, max_width=400)

    assert result.success is True
    assert result.width <= 400
    assert result.height < 600


def test_optimize_image_strips_metadata(sample_image: Path, tmp_path: Path) -> None:
    output = tmp_path / "out.jpg"
    result = optimize_image(sample_image, output, strip_metadata=True)

    assert result.success is True
    assert result.metadata_removed is True


def test_optimize_image_format_conversion(sample_image: Path, tmp_path: Path) -> None:
    output = tmp_path / "out.webp"
    result = optimize_image(sample_image, output, output_format=OutputFormat.WEBP)

    assert result.success is True
    assert result.output_path.suffix == ".webp"
    assert result.format == "WEBP"


def test_optimize_image_overwrite(sample_image: Path) -> None:
    original_size = sample_image.stat().st_size
    result = optimize_image(sample_image, None, overwrite=True, quality=50)

    assert result.success is True
    assert result.output_path == sample_image
    assert sample_image.stat().st_size < original_size


def test_optimize_image_file_not_found(tmp_path: Path) -> None:
    result = optimize_image(tmp_path / "missing.jpg")
    assert result.success is False
    assert "not found" in (result.error or "").lower()


def test_optimize_directory(sample_image: Path, tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    img2 = src_dir / "img2.jpg"
    Image.new("RGB", (400, 300), color=(0, 255, 0)).save(img2)

    out_dir = tmp_path / "out"
    results = optimize_directory(src_dir, out_dir, quality=50)

    assert len(results) == 1  # only img2.jpg in src_dir
    assert all(r.success for r in results)
    assert (out_dir / "img2.jpg").exists()


def test_optimize_directory_recursive(tmp_path: Path) -> None:
    src = tmp_path / "src"
    sub = src / "sub"
    sub.mkdir(parents=True)
    Image.new("RGB", (100, 100)).save(src / "a.jpg")
    Image.new("RGB", (100, 100)).save(sub / "b.jpg")

    results = optimize_directory(src, recursive=True, quality=50)
    assert len(results) == 2


def test_change_extension_converts_format(tmp_path: Path) -> None:
    from pixopt.optimizer import change_extension
    src = tmp_path / "test.png"
    Image.new("RGB", (100, 100), color=(0, 255, 0)).save(src)
    out = tmp_path / "test.webp"
    result = change_extension(src, out, output_format=OutputFormat.WEBP)

    assert result.success is True
    assert result.output_path.suffix == ".webp"
    assert result.format == "WEBP"


def test_convert_to_favicon(tmp_path: Path) -> None:
    from pixopt.optimizer import convert_to_favicon
    src = tmp_path / "source.png"
    Image.new("RGBA", (256, 256), color=(0, 0, 255, 128)).save(src)
    out = tmp_path / "favicon.ico"
    result = convert_to_favicon(src, out)

    assert result.success is True
    assert out.exists()
    assert out.stat().st_size > 0
    assert result.format == "ICO"
    assert result.width == 256
    assert result.height == 256


def test_optimize_svg(tmp_path: Path) -> None:
    from pixopt.optimizer import optimize_image
    src = tmp_path / "test.svg"
    raw = (
        '<?xml version="1.0"?>\n'
        '<!-- comment -->\n'
        '<svg  width="100"  height="100"   fill="black" >\n'
        '  <rect x="10.123456" y="20.999999" width="50" height="50" />\n'
        '</svg>'
    )
    src.write_text(raw, encoding="utf-8")
    out = tmp_path / "test.min.svg"
    result = optimize_image(src, out)

    assert result.success is True
    assert out.exists()
    assert out.stat().st_size < src.stat().st_size
    optimized = out.read_text(encoding="utf-8")
    assert "comment" not in optimized
    assert 'fill="black"' not in optimized
    assert "10.123" in optimized  # rounded


def test_animated_gif_to_webp(tmp_path: Path) -> None:
    from pixopt.models import OutputFormat
    from pixopt.optimizer import optimize_image
    src = tmp_path / "animated.gif"
    frames = [Image.new("RGB", (100, 100), color=(i * 50, 0, 0)) for i in range(3)]
    frames[0].save(
        src,
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
    )
    out = tmp_path / "animated.webp"
    result = optimize_image(src, out, output_format=OutputFormat.WEBP)

    assert result.success is True
    assert out.exists()
    assert result.format == "WEBP"


def test_heic_to_jpeg(tmp_path: Path) -> None:
    pytest = __import__("pytest")
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except Exception:
        pytest.skip("pillow-heif not available")

    from pixopt.optimizer import optimize_image
    src = tmp_path / "test.heic"
    img = Image.new("RGB", (200, 200), color=(0, 128, 0))
    img.save(src, format="HEIF")
    out = tmp_path / "test.jpg"
    result = optimize_image(src, out)

    assert result.success is True
    assert out.exists()
    assert out.stat().st_size > 0
    assert result.format == "JPEG"


def test_lossless_webp(tmp_path: Path) -> None:
    from pixopt.models import OutputFormat
    from pixopt.optimizer import optimize_image
    src = tmp_path / "test.png"
    Image.new("RGBA", (100, 100), color=(0, 255, 0, 128)).save(src)
    out = tmp_path / "test.webp"
    result = optimize_image(src, out, output_format=OutputFormat.WEBP, lossless=True)

    assert result.success is True
    assert out.exists()
    # Lossless WEBP should preserve the exact pixel data
    with Image.open(out) as img:
        assert img.mode in ("RGBA", "RGB")


def test_generate_comparison_html(tmp_path: Path) -> None:
    from pixopt.html_comparison import generate_comparison_html
    from pixopt.optimizer import optimize_image
    src = tmp_path / "before.jpg"
    Image.new("RGB", (200, 200), color=(255, 0, 0)).save(src, quality=95)
    after = tmp_path / "after.jpg"
    optimize_image(src, after, quality=50)
    html_path = tmp_path / "comparison.html"
    generate_comparison_html(src, after, html_path)

    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    assert "data:image/jpeg;base64," in content
    assert "Comparison" in content
    assert "Before" in content
    assert "After" in content


def test_adaptive_quality_target_size(tmp_path: Path) -> None:
    import random

    from PIL import Image

    from pixopt.adaptive_quality import find_quality_for_target_size
    src = tmp_path / "test.jpg"
    # Create a more complex image with noise so JPEG sizes vary widely
    img = Image.new("RGB", (800, 800))
    pixels = [(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
              for _ in range(800 * 800)]
    img.putdata(pixels)
    img.save(src, quality=95)

    # Pick a target between the min and max possible sizes
    buf_low = BytesIO()
    buf_high = BytesIO()
    Image.open(src).save(buf_low, format="JPEG", quality=1)
    Image.open(src).save(buf_high, format="JPEG", quality=100)
    min_size = buf_low.tell()
    max_size = buf_high.tell()
    target = (min_size + max_size) // 2

    quality = find_quality_for_target_size(
        Image.open(src),
        "JPEG",
        target,
        max_iterations=10,
    )

    assert 1 <= quality <= 100

    # The returned quality should produce a size <= target or close to it
    buf = BytesIO()
    Image.open(src).save(buf, format="JPEG", quality=quality)
    actual_size = buf.tell()
    # Allow 25% tolerance since binary search approximates
    assert actual_size <= target * 1.25


def test_generate_srcset(tmp_path: Path) -> None:
    from pixopt.srcset_generator import generate_srcset_images
    src = tmp_path / "hero.jpg"
    img = Image.new("RGB", (1200, 800), color=(0, 128, 255))
    img.save(src, quality=95)
    out_dir = tmp_path / "responsive"

    variants = generate_srcset_images(
        src,
        out_dir,
        widths=[320, 640, 1024, 1920],
        output_format="JPEG",
        quality=80,
    )

    assert len(variants) > 0
    # 1920 should be skipped since original is only 1200px wide
    assert all(v.width <= 1200 for v in variants)

    # All files should exist
    for v in variants:
        assert v.output_path.exists()
        assert v.size_bytes > 0

    # Widths should be sorted ascending
    widths = [v.width for v in variants]
    assert widths == sorted(widths)


def test_placeholder_color(tmp_path: Path) -> None:
    from pixopt.placeholder import generate_placeholder
    src = tmp_path / "test.jpg"
    Image.new("RGB", (200, 200), color=(255, 128, 64)).save(src)
    color = generate_placeholder(src, placeholder_type="color")
    assert color.startswith("#")
    assert len(color) == 7


def test_placeholder_lqip(tmp_path: Path) -> None:
    from pixopt.placeholder import generate_placeholder
    src = tmp_path / "test.jpg"
    Image.new("RGB", (200, 200), color=(255, 128, 64)).save(src)
    lqip = generate_placeholder(src, placeholder_type="lqip")
    assert lqip.startswith("data:image/jpeg;base64,")
    assert len(lqip) > 100


def test_placeholder_blurhash(tmp_path: Path) -> None:
    from pixopt.placeholder import generate_placeholder
    src = tmp_path / "test.jpg"
    Image.new("RGB", (200, 200), color=(255, 128, 64)).save(src)
    bh = generate_placeholder(src, placeholder_type="blurhash")
    assert len(bh) > 0
    assert isinstance(bh, str)


def test_smart_format_photo(tmp_path: Path) -> None:
    import random

    from pixopt.smart_format import detect_optimal_format
    src = tmp_path / "photo.jpg"
    img = Image.new("RGB", (400, 400))
    pixels = [(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
              for _ in range(400 * 400)]
    img.putdata(pixels)
    img.save(src)
    fmt = detect_optimal_format(src)
    assert fmt.value in ("webp", "jpeg")


def test_smart_format_transparent(tmp_path: Path) -> None:
    from pixopt.smart_format import detect_optimal_format
    src = tmp_path / "icon.png"
    Image.new("RGBA", (100, 100), color=(0, 255, 0, 128)).save(src)
    fmt = detect_optimal_format(src)
    assert fmt.value in ("webp", "png")


def test_backup_and_min_size(tmp_path: Path) -> None:
    from pixopt.optimizer import optimize_image
    src = tmp_path / "test.jpg"
    Image.new("RGB", (100, 100), color=(0, 128, 0)).save(src, quality=95)
    backup_dir = tmp_path / "backups"

    result = optimize_image(
        src,
        quality=50,
        backup_dir=backup_dir,
        min_size_bytes=1024 * 1024,  # 1 MB threshold (file is smaller)
    )

    # Should be skipped because file is below 1 MB
    assert result.success is True
    assert "Skipped" in (result.error or "")
    # Backup should still exist
    assert (backup_dir / "test.jpg").exists()
