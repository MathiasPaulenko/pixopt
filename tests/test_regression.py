"""Regression tests for bugs found during stabilization."""

from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.adaptive_quality import find_quality_for_target_size
from pixopt.cli import app
from pixopt.format_resolver import resolve_output_format
from pixopt.html_comparison import generate_comparison_html
from pixopt.image_ops import convert_mode, resolve_and_adjust_path, strip_metadata_pillow
from pixopt.models import OutputFormat
from pixopt.optimizer import convert_to_favicon, optimize_image
from pixopt.placeholder import (
    generate_blurhash,
    generate_lqip_datauri,
    generate_placeholder,
)
from pixopt.smart_format import detect_optimal_format
from pixopt.srcset_generator import generate_srcset_images


def test_p_palette_transparency_flattened_to_white(tmp_path: Path) -> None:
    """Paletted PNGs with transparency must be composited onto a white background."""
    source = tmp_path / "palette.png"
    output = tmp_path / "out.jpg"

    # Palette index 0 = black, marked as transparent; index 1 = red
    p = Image.new("P", (200, 200), 0)
    # Draw a red rectangle large enough to survive JPEG block compression
    for x in range(50, 150):
        for y in range(50, 150):
            p.putpixel((x, y), 1)
    palette = [0, 0, 0, 255, 0, 0] + [0] * (256 * 3 - 6)
    p.putpalette(palette)
    p.info["transparency"] = 0
    p.save(source)

    result = optimize_image(source, output, output_format=OutputFormat.JPEG)
    assert result.success is True
    assert output.exists()

    with Image.open(output) as out:
        # The transparent pixel should be close to white, definitely not black
        transparent_pixel = out.getpixel((10, 10))
        assert isinstance(transparent_pixel, tuple)
        assert all(c > 240 for c in transparent_pixel)
        # The red pixel should stay mostly red
        red_pixel = out.getpixel((100, 100))
        assert isinstance(red_pixel, tuple)
        assert red_pixel[0] > 240 and red_pixel[1] < 30 and red_pixel[2] < 30


def test_convert_mode_palette_with_transparency() -> None:
    """convert_mode must correctly flatten P+transparency to RGB."""
    img = Image.new("P", (10, 10), 0)
    img.putpixel((1, 1), 1)
    palette = [0, 0, 0, 255, 0, 0] + [0] * (256 * 3 - 6)
    img.putpalette(palette)
    img.info["transparency"] = 0

    converted = convert_mode(img, "JPEG")
    assert converted.mode == "RGB"
    assert converted.getpixel((0, 0)) == (255, 255, 255)
    assert converted.getpixel((1, 1)) == (255, 0, 0)


def test_favicon_rgb_keep_transparency_false(tmp_path: Path) -> None:
    """Favicon conversion should not crash for RGB sources when transparency is disabled."""
    source = tmp_path / "source.png"
    output = tmp_path / "out.ico"

    Image.new("RGB", (256, 256), (255, 0, 0)).save(source)

    result = convert_to_favicon(source, output, keep_transparency=False)
    assert result.success is True
    assert output.exists()


def test_comparison_html_does_not_leak_noqa(tmp_path: Path) -> None:
    """The generated comparison HTML must not contain Python # noqa markers."""
    before = tmp_path / "before.jpg"
    after = tmp_path / "after.jpg"
    out_html = tmp_path / "compare.html"

    Image.new("RGB", (100, 100), (255, 0, 0)).save(before)
    Image.new("RGB", (100, 100), (0, 255, 0)).save(after)

    generate_comparison_html(before, after, out_html)
    content = out_html.read_text(encoding="utf-8")

    assert "noqa" not in content.lower()
    assert "#" not in content or "noqa" not in content.lower()


def test_optimize_image_invalid_quality(tmp_path: Path) -> None:
    """optimize_image must reject quality outside 1-100."""
    source = tmp_path / "source.jpg"
    output = tmp_path / "out.jpg"
    Image.new("RGB", (100, 100)).save(source)

    for invalid_quality in (0, 101, -5):
        result = optimize_image(source, output, quality=invalid_quality)
        assert result.success is False
        assert result.error is not None
        assert "quality" in result.error.lower()


def test_optimize_image_invalid_max_dimensions(tmp_path: Path) -> None:
    """optimize_image must reject non-positive max_width or max_height."""
    source = tmp_path / "source.jpg"
    output = tmp_path / "out.jpg"
    Image.new("RGB", (100, 100)).save(source)

    result = optimize_image(source, output, max_width=0)
    assert result.success is False
    assert "max_width" in (result.error or "").lower()

    result = optimize_image(source, output, max_height=-1)
    assert result.success is False
    assert "max_height" in (result.error or "").lower()


def test_adaptive_quality_zero_target_size() -> None:
    """find_quality_for_target_size must raise ValueError for non-positive targets."""
    img = Image.new("RGB", (100, 100))
    with pytest.raises(ValueError, match="target_size"):
        find_quality_for_target_size(img, "JPEG", target_size=0)

    with pytest.raises(ValueError, match="target_size"):
        find_quality_for_target_size(img, "JPEG", target_size=-100)


def test_adaptive_quality_rejects_invalid_bounds() -> None:
    """find_quality_for_target_size must reject invalid bounds, tolerance and iterations."""
    img = Image.new("RGB", (100, 100))
    with pytest.raises(ValueError, match="min_quality"):
        find_quality_for_target_size(img, "JPEG", 1000, min_quality=50, max_quality=30)
    with pytest.raises(ValueError, match="max_quality"):
        find_quality_for_target_size(img, "JPEG", 1000, max_quality=200)
    with pytest.raises(ValueError, match="tolerance"):
        find_quality_for_target_size(img, "JPEG", 1000, tolerance=-0.1)
    with pytest.raises(ValueError, match="max_iterations"):
        find_quality_for_target_size(img, "JPEG", 1000, max_iterations=0)


def test_placeholder_invalid_type(tmp_path: Path) -> None:
    """generate_placeholder must raise ValueError for unknown types."""
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 100)).save(source)

    with pytest.raises(ValueError, match="placeholder_type"):
        generate_placeholder(source, placeholder_type="invalid")  # type: ignore[reportArgumentType]


def test_srcset_rejects_invalid_format_strings(tmp_path: Path) -> None:
    """Invalid format strings must raise a clear error instead of a silent fallback."""
    source = tmp_path / "source.jpg"
    out_dir = tmp_path / "responsive"
    Image.new("RGB", (800, 600)).save(source)

    with pytest.raises(ValueError, match="Unknown output format"):
        generate_srcset_images(source, out_dir, [200, 400], output_format="JPG")


def test_optimize_image_output_format_not_enum(tmp_path: Path) -> None:
    """output_format must be an OutputFormat enum, not a raw string."""
    source = tmp_path / "source.jpg"
    output = tmp_path / "out.jpg"
    Image.new("RGB", (100, 100)).save(source)

    result = optimize_image(source, output, output_format="JPEG")  # type: ignore[reportArgumentType]
    assert result.success is False
    assert "outputformat" in (result.error or "").lower()


def test_animated_webp_to_animated_webp(tmp_path: Path) -> None:
    """Animated sources other than GIF should keep all frames when output is WEBP."""
    source = tmp_path / "source.webp"
    output = tmp_path / "out.webp"

    frames = [Image.new("RGB", (100, 100), (i * 80, 0, 0)) for i in range(3)]
    frames[0].save(
        source,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
    )

    result = optimize_image(source, output, output_format=OutputFormat.WEBP)
    assert result.success is True

    with Image.open(output) as out:
        assert getattr(out, "is_animated", False) or getattr(out, "n_frames", 1) > 1


def test_decompression_bomb_is_handled(tmp_path: Path) -> None:
    """optimize_image must return a readable error for images that exceed the pixel limit."""
    source = tmp_path / "large.jpg"
    output = tmp_path / "out.jpg"
    Image.new("RGB", (100, 100)).save(source)

    original_limit = Image.MAX_IMAGE_PIXELS
    try:
        Image.MAX_IMAGE_PIXELS = 1
        result = optimize_image(source, output)
    finally:
        Image.MAX_IMAGE_PIXELS = original_limit

    assert result.success is False
    assert "decompression bomb" in (result.error or "").lower()


def test_favicon_rejects_empty_and_invalid_sizes(tmp_path: Path) -> None:
    """convert_to_favicon must reject empty, negative or zero sizes."""
    source = tmp_path / "source.png"
    output = tmp_path / "favicon.ico"
    Image.new("RGBA", (256, 256), (255, 0, 0, 0)).save(source)

    empty = convert_to_favicon(source, output, sizes=[])
    assert empty.success is False
    assert "empty" in (empty.error or "").lower()

    negative = convert_to_favicon(source, output, sizes=[-16])
    assert negative.success is False
    assert "positive" in (negative.error or "").lower()

    zero = convert_to_favicon(source, output, sizes=[0])
    assert zero.success is False
    assert "positive" in (zero.error or "").lower()


def test_strip_metadata_preserves_palette() -> None:
    """strip_metadata_pillow must keep the palette for indexed images."""
    img = Image.new("P", (100, 100), 0)
    # Set palette: index 0 = red, index 1 = green
    palette = bytes([255, 0, 0, 0, 255, 0] + [0, 0, 0] * 254)
    img.putpalette(palette)
    img.putpixel((10, 10), 1)

    clean = strip_metadata_pillow(img, "PNG")
    assert clean.getpixel((0, 0)) == 0
    assert clean.getpixel((10, 10)) == 1
    clean_palette = clean.getpalette()
    assert clean_palette is not None
    assert list(clean_palette[:6]) == [255, 0, 0, 0, 255, 0]


def test_detect_optimal_format_corrupt_file(tmp_path: Path) -> None:
    """detect_optimal_format must fall back to WEBP for corrupt images."""
    source = tmp_path / "corrupt.jpg"
    source.write_bytes(b"not an image")
    assert detect_optimal_format(source) == OutputFormat.WEBP


def test_detect_optimal_format_missing_file(tmp_path: Path) -> None:
    """detect_optimal_format must raise FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        detect_optimal_format(tmp_path / "missing.jpg")


def test_lqip_datauri_rejects_invalid_params() -> None:
    """generate_lqip_datauri must reject non-positive size or invalid quality."""
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    with pytest.raises(ValueError):
        generate_lqip_datauri(img, size=0)
    with pytest.raises(ValueError):
        generate_lqip_datauri(img, quality=0)
    with pytest.raises(ValueError):
        generate_lqip_datauri(img, quality=101)


def test_blurhash_rejects_non_positive_components() -> None:
    """generate_blurhash must reject zero or negative component counts."""
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    with pytest.raises(ValueError):
        generate_blurhash(img, components_x=0)
    with pytest.raises(ValueError):
        generate_blurhash(img, components_y=-1)


def test_resolve_and_adjust_path_adds_missing_extension() -> None:
    """resolve_and_adjust_path must add a canonical extension when the output path has none."""
    img = Image.new("RGB", (10, 10))
    adjusted, fmt = resolve_and_adjust_path(img, Path("no_extension"), OutputFormat.AUTO)
    assert adjusted == Path("no_extension.jpg")
    assert fmt == "JPEG"


def test_resolve_output_format_preserves_auto_jpeg() -> None:
    """resolve_output_format must preserve .jpeg extension for AUTO mode."""
    img = Image.new("RGB", (10, 10))
    ext, fmt = resolve_output_format(img, Path("photo.jpeg"), OutputFormat.AUTO)
    assert ext == ".jpeg"
    assert fmt == "JPEG"


def test_comparison_html_works_with_svg(tmp_path: Path) -> None:
    """generate_comparison_html must not crash when before/after are SVGs."""
    before = tmp_path / "before.svg"
    after = tmp_path / "after.svg"
    output = tmp_path / "compare.html"
    before.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
        '<rect width="100" height="50" fill="red"/></svg>',
        encoding="utf-8",
    )
    after.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
        '<rect width="100" height="50" fill="green"/></svg>',
        encoding="utf-8",
    )

    result = generate_comparison_html(before, after, output)
    assert result == output
    assert output.exists()
    assert "width: 800px;" in output.read_text(encoding="utf-8")


def test_comparison_html_escapes_title(tmp_path: Path) -> None:
    """generate_comparison_html must escape the title to avoid HTML injection."""
    before = tmp_path / "before.jpg"
    after = tmp_path / "after.jpg"
    output = tmp_path / "compare.html"
    Image.new("RGB", (10, 10), (255, 0, 0)).save(before)
    Image.new("RGB", (10, 10), (0, 255, 0)).save(after)

    generate_comparison_html(before, after, output, title="<script>alert(1)</script>")
    content = output.read_text(encoding="utf-8")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content


def test_cli_optimize_rejects_non_positive_dimensions(tmp_path: Path) -> None:
    """The optimize CLI must reject non-positive --width and --height values."""
    runner = CliRunner()
    source = tmp_path / "source.jpg"
    output = tmp_path / "out.jpg"
    Image.new("RGB", (100, 100)).save(source)

    width_result = runner.invoke(app, ["optimize", str(source), str(output), "--width", "0"])
    assert width_result.exit_code != 0

    height_result = runner.invoke(app, ["optimize", str(source), str(output), "--height", "-10"])
    assert height_result.exit_code != 0


def test_cli_srcset_escapes_special_filename_chars(tmp_path: Path) -> None:
    """The srcset CLI must URL/encode special characters in filenames for the HTML snippet."""
    runner = CliRunner()
    source = tmp_path / "img&x.jpg"
    out_dir = tmp_path / "out"
    html_file = tmp_path / "snippet.html"
    Image.new("RGB", (200, 200)).save(source)

    result = runner.invoke(
        app,
        [
            "srcset",
            str(source),
            "--sizes",
            "100",
            "--output-dir",
            str(out_dir),
            "--html",
            str(html_file),
        ],
    )
    assert result.exit_code == 0

    content = html_file.read_text(encoding="utf-8")
    assert "img&x" not in content
    assert "img%26x" in content


def test_strip_metadata_pillow_preserves_p_transparency(tmp_path: Path) -> None:
    """strip_metadata_pillow must keep the transparency info of paletted images."""
    source = tmp_path / "palette_t.png"
    output = tmp_path / "out.png"

    p = Image.new("P", (20, 20), 0)
    p.putpixel((5, 5), 1)
    palette = [0, 0, 0, 255, 0, 0] + [0] * (256 * 3 - 6)
    p.putpalette(palette)
    p.info["transparency"] = 0
    p.save(source)

    result = optimize_image(source, output)
    assert result.success is True

    with Image.open(output) as out:
        assert "transparency" in out.info
        rgba = out.convert("RGBA")
        pixel = rgba.getpixel((0, 0))
        assert isinstance(pixel, tuple)
        assert pixel[3] == 0
        rgba.close()


def test_animated_gif_to_gif_preserves_frames(tmp_path: Path) -> None:
    """Animated GIF input must keep all frames when the output stays GIF."""
    source = tmp_path / "anim.gif"
    output = tmp_path / "anim_out.gif"
    frames = [Image.new("RGB", (20, 20), (i * 60, 0, 0)) for i in range(4)]
    frames[0].save(source, save_all=True, append_images=frames[1:], duration=120, loop=0)
    for f in frames:
        f.close()

    result = optimize_image(source, output)
    assert result.success is True

    with Image.open(output) as out:
        assert getattr(out, "is_animated", False)
        assert getattr(out, "n_frames", 1) == 4


def test_animated_gif_keeps_frame_durations(tmp_path: Path) -> None:
    """Frame durations must survive animated GIF -> animated GIF optimization."""
    source = tmp_path / "anim.gif"
    output = tmp_path / "anim_out.gif"
    frames = [Image.new("RGB", (20, 20), (0, i * 60, 0)) for i in range(3)]
    frames[0].save(source, save_all=True, append_images=frames[1:], duration=250, loop=0)
    for f in frames:
        f.close()

    result = optimize_image(source, output)
    assert result.success is True

    with Image.open(output) as out:
        assert getattr(out, "is_animated", False)
        out.seek(1)
        assert out.info.get("duration") == 250


def test_batch_optimize_basename_collision(tmp_path: Path) -> None:
    """Sources sharing a basename in different dirs must not overwrite each other."""
    from pixopt.optimizer import batch_optimize

    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    Image.new("RGB", (10, 10), (255, 0, 0)).save(dir_a / "same.jpg")
    Image.new("RGB", (10, 10), (0, 0, 255)).save(dir_b / "same.jpg")
    out_dir = tmp_path / "out"

    report = batch_optimize([dir_a / "same.jpg", dir_b / "same.jpg"], out_dir)

    assert report.failed == 0
    outputs = {r.output_path.name for r in report.results}
    assert len(outputs) == 2


def test_compute_ssim_rejects_even_win_size() -> None:
    """compute_ssim must validate win_size parity and data_range sign."""
    import numpy as np

    from pixopt.quality import compute_ssim

    arr = np.zeros((16, 16), dtype=np.float32)
    with pytest.raises(ValueError):
        compute_ssim(arr, arr, win_size=8)
    with pytest.raises(ValueError):
        compute_ssim(arr, arr, win_size=0)
    with pytest.raises(ValueError):
        compute_ssim(arr, arr, data_range=0)


def test_generate_srcset_rejects_unknown_format(tmp_path: Path) -> None:
    """generate_srcset_images must raise ValueError for unknown format strings."""
    source = tmp_path / "img.jpg"
    Image.new("RGB", (200, 200)).save(source)
    with pytest.raises(ValueError):
        generate_srcset_images(source, tmp_path / "out", [100], output_format="bogus")


def test_scan_directory_limits_all_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """MAX_SCAN_ENTRIES must cap total scanned entries, not only valid ones."""
    import pixopt.inventory as inventory

    for i in range(5):
        (tmp_path / f"broken_{i}.jpg").write_bytes(b"not an image")

    monkeypatch.setattr(inventory, "MAX_SCAN_ENTRIES", 3)
    report = inventory.scan_directory(tmp_path)

    # The cap counts every processed entry, including unreadable files.
    assert len(report.entries) == 3
    assert report.errors == 3


def test_cli_compare_with_format_conversion(tmp_path: Path) -> None:
    """`pixopt compare -f webp` must not crash on the adjusted output suffix."""
    runner = CliRunner()
    source = tmp_path / "photo.png"
    html = tmp_path / "cmp.html"
    Image.new("RGB", (40, 40), (200, 0, 0)).save(source)

    result = runner.invoke(app, ["compare", str(source), str(html), "-f", "webp"])
    assert result.exit_code == 0
    assert html.exists()


def test_cli_srcset_short_flag_means_sizes(tmp_path: Path) -> None:
    """In `pixopt srcset`, -s must map to --sizes, not --strip."""
    runner = CliRunner()
    source = tmp_path / "img.jpg"
    out_dir = tmp_path / "out"
    Image.new("RGB", (300, 300)).save(source)

    result = runner.invoke(app, ["srcset", str(source), "-s", "100", "-o", str(out_dir)])
    assert result.exit_code == 0
    assert (out_dir / "img-100w.webp").exists()


def test_cli_optimize_preset_applies_quality(tmp_path: Path) -> None:
    """--preset must apply preset values for options the user did not pass."""
    runner = CliRunner()
    source = tmp_path / "photo.jpg"
    output = tmp_path / "out.jpg"
    Image.new("RGB", (800, 800), (123, 45, 67)).save(source)

    # The "thumbnail" preset caps max-width at 300 and uses fit=cover.
    result = runner.invoke(app, ["optimize", str(source), str(output), "--preset", "thumbnail"])
    assert result.exit_code == 0
    with Image.open(output) as out:
        assert out.width <= 300


def test_cli_optimize_preset_quality_takes_effect(tmp_path: Path) -> None:
    """A preset's quality must be used when the user does not pass -q."""
    runner = CliRunner()
    source = tmp_path / "photo.jpg"
    Image.new("RGB", (400, 400), (200, 100, 50)).save(source)

    result_default = runner.invoke(app, ["optimize", str(source), str(tmp_path / "def.jpg")])
    result_print = runner.invoke(
        app, ["optimize", str(source), str(tmp_path / "print.jpg"), "--preset", "print"]
    )
    assert result_default.exit_code == 0
    assert result_print.exit_code == 0

    # "print" uses quality=100 and baseline encoding; if the preset is
    # applied the output must differ from the default q85/progressive run.
    assert (tmp_path / "print.jpg").stat().st_size != (tmp_path / "def.jpg").stat().st_size


def test_cli_optimize_explicit_quality_overrides_preset(tmp_path: Path) -> None:
    """An explicit -q still wins over the preset value."""
    runner = CliRunner()
    source = tmp_path / "photo.jpg"
    Image.new("RGB", (400, 400), (200, 100, 50)).save(source)

    result_low = runner.invoke(
        app, ["optimize", str(source), str(tmp_path / "low.jpg"), "-q", "10"]
    )
    result_preset = runner.invoke(
        app,
        [
            "optimize",
            str(source),
            str(tmp_path / "preset.jpg"),
            "-q",
            "10",
            "--preset",
            "print",
        ],
    )
    assert result_low.exit_code == 0
    assert result_preset.exit_code == 0

    # Explicit -q 10 must override preset quality=100 → same order of size.
    low_size = (tmp_path / "low.jpg").stat().st_size
    preset_size = (tmp_path / "preset.jpg").stat().st_size
    assert abs(low_size - preset_size) < low_size
