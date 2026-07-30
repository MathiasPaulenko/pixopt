"""Unit tests for low-level library modules."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from pixopt.adaptive_quality import find_quality_for_target_size
from pixopt.format_resolver import resolve_output_format
from pixopt.html_comparison import generate_comparison_html
from pixopt.optimizer import (
    change_extension,
    convert_to_favicon,
    optimize_directory,
    optimize_image,
)
from pixopt.image_ops import (
    _pixel_data,
    build_save_kwargs,
    convert_mode,
    resize_image,
    resolve_and_adjust_path,
    strip_exif_post_process,
    strip_metadata_pillow,
)
from pixopt.models import OptimizationResult, OutputFormat, _human_readable_size
from pixopt.placeholder import (
    PlaceholderType,
    extract_dominant_color,
    generate_blurhash,
    generate_lqip_datauri,
    generate_placeholder,
)
from pixopt.smart_format import (
    count_unique_colors,
    detect_optimal_format,
    has_transparency,
    is_photo,
)
from pixopt.svg_optimizer import optimize_svg
from pixopt.utils import discover_images


@pytest.fixture
def photo_image() -> Image.Image:
    img = Image.new("RGB", (100, 100))
    for y in range(100):
        for x in range(100):
            img.putpixel((x, y), (x * 2, y * 2, 128))
    return img


def test_human_readable_size() -> None:
    assert _human_readable_size(512) == "512 B"
    assert _human_readable_size(2048) == "2.00 KB"
    assert _human_readable_size(2 * 1024 * 1024) == "2.00 MB"


def test_optimization_result_human_properties() -> None:
    result = OptimizationResult(
        source_path=Path("in.jpg"),
        output_path=Path("out.jpg"),
        original_size=2048,
        optimized_size=1024,
        savings_bytes=1024,
        savings_percent=50.0,
        width=10,
        height=10,
        format="JPEG",
        metadata_removed=True,
        success=True,
    )
    assert result.human_original_size == "2.00 KB"
    assert result.human_optimized_size == "1.00 KB"
    assert result.human_savings == "1.00 KB"


def test_convert_mode_png_untouched() -> None:
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
    assert convert_mode(img, "PNG") is img


def test_convert_mode_unknown_format() -> None:
    img = Image.new("RGB", (10, 10))
    assert convert_mode(img, "GIF") is img


def test_convert_mode_jpeg_flattens_rgba() -> None:
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
    converted = convert_mode(img, "JPEG")
    assert converted.mode == "RGB"


def test_convert_mode_jpeg_flattens_la() -> None:
    img = Image.new("LA", (10, 10), (128, 128))
    converted = convert_mode(img, "JPEG")
    assert converted.mode == "RGB"


def test_convert_mode_jpeg_palette_with_transparency() -> None:
    img = Image.new("P", (10, 10), 0)
    palette = [255, 255, 255, 255, 0, 0] + [0] * (256 * 3 - 6)
    img.putpalette(palette)
    img.info["transparency"] = 0
    img.putpixel((5, 5), 1)
    converted = convert_mode(img, "JPEG")
    assert converted.mode == "RGB"


def test_resize_image_no_bounds() -> None:
    img = Image.new("RGB", (100, 100))
    assert resize_image(img) is img


def test_resize_image_exact_dimensions() -> None:
    img = Image.new("RGB", (100, 100))
    resized = resize_image(img, max_width=50, max_height=50, keep_aspect_ratio=False)
    assert resized.size == (50, 50)


def test_build_save_kwargs_png() -> None:
    kwargs = build_save_kwargs("PNG")
    assert kwargs["compress_level"] == 9


def test_build_save_kwargs_gif_animated() -> None:
    kwargs = build_save_kwargs("GIF", animated=True)
    assert kwargs["save_all"] is True


def test_strip_metadata_pillow_jpeg() -> None:
    img = Image.new("RGB", (10, 10))
    assert strip_metadata_pillow(img, "JPEG") is img


def test_strip_metadata_pillow_png() -> None:
    img = Image.new("P", (10, 10), 0)
    palette = [255, 0, 0, 0, 255, 0] + [0] * (256 * 3 - 6)
    img.putpalette(palette)
    img.putpixel((5, 5), 1)
    clean = strip_metadata_pillow(img, "PNG")
    assert clean.getpixel((0, 0)) == 0
    assert list(clean.getpalette()[:6]) == [255, 0, 0, 0, 255, 0]


def test_resolve_and_adjust_path_unknown_suffix(photo_image: Image.Image, tmp_path: Path) -> None:
    out = tmp_path / "foo"
    adjusted, fmt = resolve_and_adjust_path(photo_image, out, OutputFormat.AUTO)
    assert adjusted.suffix == ".jpg"
    assert fmt == "JPEG"


def test_pixel_data_fallback() -> None:
    class FakeImg:
        def getdata(self) -> list[tuple[int, int, int]]:
            return [(255, 0, 0), (0, 255, 0)]

    data = _pixel_data(FakeImg())  # type: ignore[arg-type]
    assert data == [(255, 0, 0), (0, 255, 0)]


def test_strip_exif_post_process_skips_png() -> None:
    # Should not raise and not modify the file.
    path = Path("does_not_matter.png")
    strip_exif_post_process(path, "PNG")


def test_has_transparency_rgba_true() -> None:
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
    assert has_transparency(img) is True


def test_has_transparency_rgba_opaque() -> None:
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
    assert has_transparency(img) is False


def test_has_transparency_p_with_transparency() -> None:
    img = Image.new("P", (10, 10), 0)
    img.info["transparency"] = 0
    assert has_transparency(img) is True


def test_has_transparency_p_without_transparency() -> None:
    img = Image.new("P", (10, 10), 0)
    assert has_transparency(img) is False


def test_count_unique_colors_capped(photo_image: Image.Image) -> None:
    assert count_unique_colors(photo_image, max_colors=10) == 10


def test_is_photo_true(photo_image: Image.Image) -> None:
    assert is_photo(photo_image) is True


def test_is_photo_false() -> None:
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    assert is_photo(img) is False


def test_detect_optimal_format_photo(tmp_path: Path) -> None:
    img = Image.new("RGB", (100, 100))
    for y in range(100):
        for x in range(100):
            img.putpixel((x, y), (x, y, 128))
    src = tmp_path / "photo.jpg"
    img.save(src)
    fmt = detect_optimal_format(src)
    assert fmt == OutputFormat.WEBP


def test_detect_optimal_format_transparent(tmp_path: Path) -> None:
    src = tmp_path / "transparent.png"
    Image.new("RGBA", (100, 100), (255, 0, 0, 128)).save(src)
    fmt = detect_optimal_format(src)
    assert fmt == OutputFormat.WEBP


def test_detect_optimal_format_transparent_no_lossless(tmp_path: Path) -> None:
    src = tmp_path / "transparent.png"
    Image.new("RGBA", (100, 100), (255, 0, 0, 128)).save(src)
    fmt = detect_optimal_format(src, allow_lossless=False)
    assert fmt == OutputFormat.PNG


def test_detect_optimal_format_animated(tmp_path: Path) -> None:
    src = tmp_path / "anim.gif"
    frames = [Image.new("RGB", (10, 10), (i * 50, 0, 0)) for i in range(2)]
    frames[0].save(src, save_all=True, append_images=frames[1:], duration=100, loop=0)
    fmt = detect_optimal_format(src, allow_animation=True)
    assert fmt == OutputFormat.WEBP


def test_detect_optimal_format_lossy_only(tmp_path: Path) -> None:
    src = tmp_path / "red.jpg"
    Image.new("RGB", (100, 100), (255, 0, 0)).save(src)
    fmt = detect_optimal_format(src, allow_lossless=False)
    assert fmt == OutputFormat.JPEG


def test_detect_optimal_format_lossless_only(tmp_path: Path) -> None:
    src = tmp_path / "red.jpg"
    Image.new("RGB", (100, 100), (255, 0, 0)).save(src)
    fmt = detect_optimal_format(src, allow_lossy=False)
    assert fmt == OutputFormat.WEBP


def test_detect_optimal_format_both_disabled(tmp_path: Path) -> None:
    src = tmp_path / "red.jpg"
    Image.new("RGB", (100, 100), (255, 0, 0)).save(src)
    fmt = detect_optimal_format(src, allow_lossy=False, allow_lossless=False)
    assert fmt == OutputFormat.PNG


def test_detect_optimal_format_corrupt(tmp_path: Path) -> None:
    src = tmp_path / "corrupt.jpg"
    src.write_bytes(b"not an image")
    fmt = detect_optimal_format(src)
    assert fmt == OutputFormat.WEBP


def test_extract_dominant_color() -> None:
    img = Image.new("RGB", (10, 10), (255, 128, 64))
    assert extract_dominant_color(img) == "#ff8040"


def test_extract_dominant_color_non_tuple(tmp_path: Path) -> None:
    # Single-pixel image may return an int from getpixel on some Pillow versions.
    img = Image.new("L", (1, 1))
    color = extract_dominant_color(img)
    assert color.startswith("#")


def test_generate_lqip_datauri_invalid() -> None:
    img = Image.new("RGB", (10, 10))
    with pytest.raises(ValueError):
        generate_lqip_datauri(img, size=0)
    with pytest.raises(ValueError):
        generate_lqip_datauri(img, quality=0)


def test_generate_blurhash_invalid() -> None:
    img = Image.new("RGB", (10, 10))
    with pytest.raises(ValueError):
        generate_blurhash(img, components_x=0)


def test_generate_placeholder_types(tmp_path: Path) -> None:
    src = tmp_path / "test.jpg"
    Image.new("RGB", (50, 50), (128, 64, 32)).save(src)
    color = generate_placeholder(src, placeholder_type="color")
    assert color.startswith("#")
    lqip = generate_placeholder(src, placeholder_type="lqip")
    assert lqip.startswith("data:image/jpeg")
    blur = generate_placeholder(src, placeholder_type="blurhash")
    assert len(blur) > 0


def test_generate_placeholder_default(tmp_path: Path) -> None:
    src = tmp_path / "test.jpg"
    Image.new("RGB", (50, 50)).save(src)
    result = generate_placeholder(src)
    assert result.startswith("data:image/jpeg")


def test_optimize_svg_comments_and_cdata() -> None:
    raw = (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN">\n'
        '<!-- comment -->\n'
        '<svg width="100" height="100">\n'
        '<![CDATA[ <some>content</some> ]]>\n'
        '<rect x="10.123456" y="20.0" width="50" height="50" opacity="1"/>\n'
        '</svg>'
    )
    optimized = optimize_svg(raw)
    assert "<!-- comment -->" not in optimized
    assert "<!DOCTYPE" not in optimized
    assert 'opacity="1"' not in optimized
    assert "10.123" in optimized
    assert "<some>content</some>" in optimized


def test_optimize_svg_bytes() -> None:
    raw = b'<svg width="10" height="10"></svg>'
    optimized = optimize_svg(raw)
    assert "<svg" in optimized


def test_optimize_svg_quotes() -> None:
    raw = '<svg width="10" height="10"><rect fill="red\\" stroke="blue"/></svg>'
    optimized = optimize_svg(raw)
    assert "<svg" in optimized


def test_optimize_svg_both_quote_styles() -> None:
    # Unquoted attribute containing both quote characters triggers quote escaping.
    raw = '<svg width="10" height="10"><rect fill=abc\'"def/></svg>'
    optimized = optimize_svg(raw)
    assert "<svg" in optimized


def test_optimize_svg_single_quote_with_double_quote() -> None:
    # Single-quoted value with a double quote covers _quote line 78.
    raw = '<svg width="10" height="10"><rect fill=\'red"blue\'/></svg>'
    optimized = optimize_svg(raw)
    assert "fill='red\"blue'" in optimized


def test_optimize_svg_empty_attribute() -> None:
    raw = '<svg width="10" height="10"><rect fill=""/></svg>'
    optimized = optimize_svg(raw)
    assert "<svg" in optimized
    assert "fill" not in optimized


def test_optimize_svg_invalid_tag() -> None:
    raw = '<svg width="10" height="10">< not-a-tag /></svg>'
    optimized = optimize_svg(raw)
    assert "< not-a-tag />" in optimized


def test_discover_images_recursive(tmp_path: Path) -> None:
    d = tmp_path / "src"
    (d / "sub").mkdir(parents=True)
    Image.new("RGB", (10, 10)).save(d / "a.jpg")
    Image.new("RGB", (10, 10)).save(d / "sub" / "b.jpg")
    (d / "c.txt").write_text("not an image", encoding="utf-8")
    found = list(discover_images(d, recursive=True))
    assert len(found) == 2


def test_discover_images_non_recursive(tmp_path: Path) -> None:
    d = tmp_path / "src"
    (d / "sub").mkdir(parents=True)
    Image.new("RGB", (10, 10)).save(d / "a.jpg")
    Image.new("RGB", (10, 10)).save(d / "sub" / "b.jpg")
    found = list(discover_images(d, recursive=False))
    assert len(found) == 1


def test_discover_images_extensions_filter(tmp_path: Path) -> None:
    d = tmp_path / "src"
    d.mkdir()
    Image.new("RGB", (10, 10)).save(d / "a.jpg")
    Image.new("RGB", (10, 10)).save(d / "b.png")
    found = list(discover_images(d, extensions={".png"}))
    assert len(found) == 1
    assert found[0].suffix == ".png"


def test_discover_images_skips_symlink_escape(tmp_path: Path) -> None:
    d = tmp_path / "src"
    d.mkdir()
    outside = tmp_path / "outside.jpg"
    Image.new("RGB", (10, 10)).save(outside)
    try:
        (d / "link.jpg").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks require privileges on this platform")
    found = list(discover_images(d, recursive=False))
    assert not any("link" in f.name for f in found)


def test_resolve_output_format_original(tmp_path: Path) -> None:
    src = tmp_path / "source.jpeg"
    Image.new("RGB", (10, 10)).save(src, format="JPEG")
    with Image.open(src) as img:
        ext, fmt = resolve_output_format(img, tmp_path / "out.jpg", OutputFormat.ORIGINAL)
    assert ext == ".jpeg"
    assert fmt == "JPEG"


def test_resolve_output_format_auto_no_suffix(photo_image: Image.Image, tmp_path: Path) -> None:
    ext, fmt = resolve_output_format(photo_image, tmp_path / "noext", OutputFormat.AUTO)
    assert ext == ".jpg"
    assert fmt == "JPEG"


def test_resolve_output_format_auto_unknown_suffix(photo_image: Image.Image, tmp_path: Path) -> None:
    ext, fmt = resolve_output_format(photo_image, tmp_path / "file.xyz", OutputFormat.AUTO)
    assert ext == ".jpg"
    assert fmt == "JPEG"


def test_resolve_output_format_explicit_png() -> None:
    img = Image.new("RGB", (10, 10))
    ext, fmt = resolve_output_format(img, Path("out.jpg"), OutputFormat.PNG)
    assert ext == ".png"
    assert fmt == "PNG"


def test_adaptive_quality_non_jpeg_webp(photo_image: Image.Image) -> None:
    quality = find_quality_for_target_size(photo_image, "PNG", 1000)
    assert quality == 85


def test_adaptive_quality_lossless(photo_image: Image.Image) -> None:
    quality = find_quality_for_target_size(
        photo_image, "WEBP", 1000, lossless=True, max_iterations=10,
    )
    assert 1 <= quality <= 100


def test_adaptive_quality_with_resize(photo_image: Image.Image) -> None:
    quality = find_quality_for_target_size(
        photo_image, "JPEG", 5000, max_width=50, max_height=50, max_iterations=10,
    )
    assert 1 <= quality <= 100


def test_adaptive_quality_invalid_min_quality(photo_image: Image.Image) -> None:
    with pytest.raises(ValueError):
        find_quality_for_target_size(photo_image, "JPEG", 1000, min_quality=0)
    with pytest.raises(ValueError):
        find_quality_for_target_size(photo_image, "JPEG", 1000, min_quality=101)


def test_html_comparison_large_file(tmp_path: Path) -> None:
    before = tmp_path / "large.jpg"
    after = tmp_path / "large2.jpg"
    size = (1024 * 1024) + 1
    before.write_bytes(b"\0" * size)
    after.write_bytes(b"\0" * size)
    html = generate_comparison_html(before, after, tmp_path / "compare.html")
    content = html.read_text()
    assert "1.00 MB" in content


def test_optimize_image_missing_source(tmp_path: Path) -> None:
    missing = tmp_path / "missing.jpg"
    result = optimize_image(missing, tmp_path / "out.jpg")
    assert not result.success
    assert "not found" in (result.error or "").lower()


def test_optimize_image_invalid_output_format(tmp_path: Path) -> None:
    src = tmp_path / "test.jpg"
    Image.new("RGB", (10, 10)).save(src)
    result = optimize_image(src, tmp_path / "out.jpg", output_format="JPEG")  # type: ignore[arg-type]
    assert not result.success


def test_optimize_image_output_required(tmp_path: Path) -> None:
    src = tmp_path / "test.jpg"
    Image.new("RGB", (10, 10)).save(src)
    result = optimize_image(src, None, overwrite=False)
    assert not result.success
    assert "output" in (result.error or "").lower()


def test_optimize_image_min_size_negative(tmp_path: Path) -> None:
    src = tmp_path / "test.jpg"
    Image.new("RGB", (10, 10)).save(src)
    result = optimize_image(src, tmp_path / "out.jpg", min_size_bytes=-1)
    assert not result.success
    assert "min_size" in (result.error or "").lower()


def test_optimize_image_below_min_size(tmp_path: Path) -> None:
    src = tmp_path / "test.jpg"
    Image.new("RGB", (10, 10)).save(src)
    result = optimize_image(src, tmp_path / "out.jpg", min_size_bytes=src.stat().st_size + 1)
    assert result.success
    assert "skipped" in (result.error or "").lower()


def test_optimize_image_corrupt(tmp_path: Path) -> None:
    src = tmp_path / "corrupt.jpg"
    src.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    result = optimize_image(src, tmp_path / "out.jpg")
    assert not result.success


def test_optimize_svg_invalid_utf8(tmp_path: Path) -> None:
    src = tmp_path / "bad.svg"
    src.write_bytes(b"\xff\xfe<svg></svg>")
    result = optimize_image(src, tmp_path / "out.svg")
    assert not result.success


def test_convert_to_favicon_default_output(tmp_path: Path) -> None:
    src = tmp_path / "logo.png"
    Image.new("RGBA", (256, 256)).save(src)
    result = convert_to_favicon(src)
    assert result.success
    assert result.output_path == src.with_suffix(".ico")


def test_convert_to_favicon_output_without_suffix(tmp_path: Path) -> None:
    src = tmp_path / "logo.png"
    Image.new("RGBA", (256, 256)).save(src)
    out = tmp_path / "favicon"
    result = convert_to_favicon(src, out)
    assert result.success
    assert result.output_path == out.with_suffix(".ico")


def test_convert_to_favicon_corrupt(tmp_path: Path) -> None:
    src = tmp_path / "corrupt.jpg"
    src.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    result = convert_to_favicon(src, tmp_path / "favicon.ico")
    assert not result.success


def test_change_extension_overwrite_in_place(tmp_path: Path) -> None:
    src = tmp_path / "test.jpg"
    Image.new("RGB", (10, 10)).save(src)
    result = change_extension(src, None, overwrite=True, output_format=OutputFormat.WEBP)
    assert result.success
    assert (tmp_path / "test.webp").exists()


def test_optimize_directory_output_none(tmp_path: Path) -> None:
    d = tmp_path / "src"
    d.mkdir()
    Image.new("RGB", (50, 50)).save(d / "a.jpg")
    results = optimize_directory(d, output_dir=None)
    assert len(results) == 1
    assert all(r.success for r in results)


def test_convert_to_favicon_missing_source(tmp_path: Path) -> None:
    result = convert_to_favicon(tmp_path / "missing.png")
    assert not result.success
    assert "not found" in (result.error or "").lower()

