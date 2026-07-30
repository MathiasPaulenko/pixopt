"""Integration tests for the pixopt CLI."""

from __future__ import annotations

import io
import sys
import webbrowser
from pathlib import Path
from typing import Generator

import pytest
from PIL import Image
from rich.console import Console
from typer.testing import CliRunner

from pixopt.cli import app
from pixopt.cli import output as output_module
from pixopt.models import OptimizationResult, OutputFormat


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner(mix_stderr=False)


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    img_path = tmp_path / "test.jpg"
    Image.new("RGB", (800, 600), color=(255, 0, 0)).save(img_path, quality=95)
    return img_path


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    d = tmp_path / "images"
    d.mkdir()
    Image.new("RGB", (200, 200), color=(255, 0, 0)).save(d / "a.jpg")
    Image.new("RGB", (200, 200), color=(0, 255, 0)).save(d / "b.png")
    return d


@pytest.fixture
def _capture_console() -> Generator[Console, None, None]:
    original = output_module.console
    capture = Console(file=io.StringIO(), force_terminal=True, highlight=False)
    output_module.console = capture
    try:
        yield capture
    finally:
        output_module.console = original


def test_no_args_shows_help(runner: CliRunner) -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_optimize_single_file(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.jpg"
    result = runner.invoke(app, ["optimize", str(sample_image), str(out), "--quality", "50"])
    assert result.exit_code == 0
    assert out.exists()


def test_optimize_overwrite_in_place(runner: CliRunner, sample_image: Path) -> None:
    result = runner.invoke(app, ["optimize", str(sample_image), "--overwrite", "--quality", "50"])
    assert result.exit_code == 0
    assert sample_image.exists()


def test_optimize_directory(runner: CliRunner, sample_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "optimized"
    result = runner.invoke(app, ["optimize", str(sample_dir), str(out), "--recursive"])
    assert result.exit_code == 0
    assert (out / "a.jpg").exists()
    assert (out / "b.png").exists()


def test_optimize_smart_format(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(app, ["optimize", str(sample_image), str(out), "--smart-format"])
    assert result.exit_code == 0


def test_optimize_target_size(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.jpg"
    result = runner.invoke(
        app,
        ["optimize", str(sample_image), str(out), "--target-size", "20"],
    )
    assert result.exit_code == 0
    assert out.exists()


def test_optimize_invalid_quality(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.jpg"
    result = runner.invoke(app, ["optimize", str(sample_image), str(out), "--quality", "150"])
    assert result.exit_code != 0


def test_optimize_missing_file(runner: CliRunner, tmp_path: Path) -> None:
    missing = tmp_path / "missing.jpg"
    result = runner.invoke(app, ["optimize", str(missing), str(tmp_path / "out.jpg")])
    assert result.exit_code != 0


def test_batch_command(runner: CliRunner, sample_dir: Path, tmp_path: Path) -> None:
    a = sample_dir / "a.jpg"
    b = sample_dir / "b.png"
    out = tmp_path / "batch_out"
    result = runner.invoke(
        app,
        ["batch", str(a), str(b), "-o", str(out), "--quality", "50"],
    )
    assert result.exit_code == 0
    assert (out / "a.jpg").exists()
    assert (out / "b.png").exists()


def test_convert_file(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.webp"
    result = runner.invoke(app, ["convert", str(sample_image), str(out), "-f", "webp"])
    assert result.exit_code == 0
    assert out.exists()
    assert out.suffix == ".webp"


def test_convert_directory(runner: CliRunner, sample_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "converted"
    result = runner.invoke(app, ["convert", str(sample_dir), str(out), "--recursive", "-f", "webp"])
    assert result.exit_code == 0
    assert (out / "a.webp").exists()
    assert (out / "b.webp").exists()


def test_convert_smart_format(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(app, ["convert", str(sample_image), str(out), "--smart-format"])
    assert result.exit_code == 0


def test_compare_command(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    html = tmp_path / "compare.html"
    result = runner.invoke(app, ["compare", str(sample_image), str(html), "--quality", "50"])
    assert result.exit_code == 0
    assert html.exists()


def test_compare_command_failure(runner: CliRunner, tmp_path: Path) -> None:
    missing = tmp_path / "missing.jpg"
    html = tmp_path / "compare.html"
    result = runner.invoke(app, ["compare", str(missing), str(html)])
    assert result.exit_code != 0


def test_info_command(runner: CliRunner, sample_image: Path) -> None:
    result = runner.invoke(app, ["info", str(sample_image)])
    assert result.exit_code == 0
    assert "800x600" in result.output


def test_info_command_corrupt(runner: CliRunner, tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.jpg"
    corrupt.write_bytes(b"not an image")
    result = runner.invoke(app, ["info", str(corrupt)])
    assert result.exit_code != 0


def test_favicon_command(runner: CliRunner, tmp_path: Path) -> None:
    src = tmp_path / "logo.png"
    Image.new("RGBA", (256, 256), color=(255, 0, 0, 128)).save(src)
    out = tmp_path / "favicon.ico"
    result = runner.invoke(app, ["favicon", str(src), str(out)])
    assert result.exit_code == 0
    assert out.exists()


def test_favicon_command_invalid_size(runner: CliRunner, tmp_path: Path) -> None:
    src = tmp_path / "logo.png"
    Image.new("RGBA", (256, 256), color=(255, 0, 0, 128)).save(src)
    out = tmp_path / "favicon.ico"
    result = runner.invoke(app, ["favicon", str(src), str(out), "--size", "0"])
    combined = (result.stdout or "") + (result.stderr or "")
    assert "favicon sizes" in combined


def test_favicon_command_missing_source(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "favicon.ico"
    result = runner.invoke(app, ["favicon", str(tmp_path / "missing.png"), str(out)])
    assert result.exit_code != 0


def test_placeholder_color(runner: CliRunner, sample_image: Path) -> None:
    result = runner.invoke(app, ["placeholder", str(sample_image), "--type", "color"])
    assert result.exit_code == 0
    assert "#" in result.output


def test_placeholder_lqip(runner: CliRunner, sample_image: Path) -> None:
    result = runner.invoke(app, ["placeholder", str(sample_image), "--type", "lqip"])
    assert result.exit_code == 0
    assert "data:image/jpeg" in result.output


def test_placeholder_blurhash(runner: CliRunner, sample_image: Path) -> None:
    result = runner.invoke(app, ["placeholder", str(sample_image), "--type", "blurhash"])
    assert result.exit_code == 0


def test_placeholder_output_file(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "blurhash.txt"
    result = runner.invoke(app, ["placeholder", str(sample_image), "--type", "blurhash", "-o", str(out)])
    assert result.exit_code == 0
    assert out.exists()


def test_placeholder_invalid_type(runner: CliRunner, sample_image: Path) -> None:
    result = runner.invoke(app, ["placeholder", str(sample_image), "--type", "invalid"])
    assert result.exit_code != 0


def test_srcset_command(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "responsive"
    html = tmp_path / "snippet.html"
    result = runner.invoke(
        app,
        ["srcset", str(sample_image), "--sizes", "200,400", "-o", str(out), "--html", str(html)],
    )
    assert result.exit_code == 0
    assert html.exists()


def test_srcset_invalid_format(runner: CliRunner, sample_image: Path) -> None:
    result = runner.invoke(
        app,
        ["srcset", str(sample_image), "--sizes", "200", "-f", "invalid"],
    )
    assert result.exit_code != 0


def test_srcset_invalid_sizes(runner: CliRunner, sample_image: Path) -> None:
    result = runner.invoke(
        app,
        ["srcset", str(sample_image), "--sizes", "abc"],
    )
    assert result.exit_code != 0


def test_human_size() -> None:
    assert output_module._human_size(512) == "512 B"
    assert output_module._human_size(2048) == "2.00 KB"
    assert output_module._human_size(2 * 1024 * 1024) == "2.00 MB"


def test_print_result_success(_capture_console: Console) -> None:
    result = OptimizationResult(
        source_path=Path("source.jpg"),
        output_path=Path("output.jpg"),
        original_size=2048,
        optimized_size=1024,
        savings_bytes=1024,
        savings_percent=50.0,
        width=100,
        height=100,
        format="JPEG",
        metadata_removed=True,
        success=True,
    )
    output_module._print_result(result)
    text = _capture_console.file.getvalue()
    assert "Optimized" in text
    assert "output.jpg" in text
    assert "50.0%" in text


def test_print_result_failure(_capture_console: Console) -> None:
    result = OptimizationResult(
        source_path=Path("source.jpg"),
        output_path=Path("output.jpg"),
        original_size=2048,
        optimized_size=0,
        savings_bytes=0,
        savings_percent=0.0,
        width=0,
        height=0,
        format="",
        metadata_removed=False,
        success=False,
        error="broken",
    )
    output_module._print_result(result)
    text = _capture_console.file.getvalue()
    assert "Error" in text
    assert "broken" in text


def test_print_summary(_capture_console: Console) -> None:
    results = [
        OptimizationResult(
            source_path=Path("a.jpg"),
            output_path=Path("a.jpg"),
            original_size=2000,
            optimized_size=1000,
            savings_bytes=1000,
            savings_percent=50.0,
            width=100,
            height=100,
            format="JPEG",
            metadata_removed=True,
            success=True,
        ),
        OptimizationResult(
            source_path=Path("b.jpg"),
            output_path=Path("b.jpg"),
            original_size=0,
            optimized_size=0,
            savings_bytes=0,
            savings_percent=0.0,
            width=0,
            height=0,
            format="",
            metadata_removed=False,
            success=False,
            error="fail",
        ),
    ]
    output_module._print_summary(results)
    text = _capture_console.file.getvalue()
    assert "Optimization Summary" in text
    assert "1/2" in text
    assert "Saved" in text


def test_print_summary_empty(_capture_console: Console) -> None:
    output_module._print_summary([])
    text = _capture_console.file.getvalue()
    assert "Optimization Summary" in text


@pytest.mark.skipif(sys.platform == "win32", reason="webbrowser open is not testable")
def test_compare_open_browser(runner: CliRunner, sample_image: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    html = tmp_path / "compare.html"
    opened: list[str] = []
    monkeypatch.setattr(webbrowser, "open", opened.append)
    result = runner.invoke(app, ["compare", str(sample_image), str(html), "--open"])
    assert result.exit_code == 0
    assert any(str(html) in url for url in opened)


def test_compare_command_directory_source(runner: CliRunner, tmp_path: Path) -> None:
    html = tmp_path / "compare.html"
    result = runner.invoke(app, ["compare", str(tmp_path), str(html)])
    assert result.exit_code != 0


def test_info_command_exif(runner: CliRunner, tmp_path: Path) -> None:
    import piexif

    src = tmp_path / "exif.jpg"
    img = Image.new("RGB", (100, 100))
    exif = piexif.dump({
        "0th": {piexif.ImageIFD.Make: b"TestMaker"},
    })
    img.save(src, exif=exif)
    result = runner.invoke(app, ["info", str(src)])
    assert result.exit_code == 0
    assert "TestMaker" in result.output


def test_info_command_directory(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["info", str(tmp_path)])
    assert result.exit_code != 0


def test_optimize_target_size_png(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.png"
    result = runner.invoke(
        app,
        ["optimize", str(sample_image), str(out), "--format", "png", "--target-size", "100"],
    )
    assert result.exit_code == 0
    assert out.exists()


def test_srcset_empty_sizes(runner: CliRunner, sample_image: Path) -> None:
    result = runner.invoke(app, ["srcset", str(sample_image), "--sizes", ""])
    assert result.exit_code != 0


def test_srcset_no_variants(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "responsive"
    result = runner.invoke(
        app,
        ["srcset", str(sample_image), "--sizes", "5000", "-o", str(out)],
    )
    assert result.exit_code != 0


def test_srcset_html_outside_output_dir(runner: CliRunner, sample_image: Path, tmp_path: Path) -> None:
    out = tmp_path / "responsive"
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    html = html_dir / "snippet.html"
    result = runner.invoke(
        app,
        ["srcset", str(sample_image), "--sizes", "200", "-o", str(out), "--html", str(html)],
    )
    assert result.exit_code == 0
    assert html.exists()


def test_cli_module_main(monkeypatch: pytest.MonkeyPatch) -> None:
    import runpy

    monkeypatch.setattr(sys, "argv", ["pixopt.cli", "--help"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("pixopt.cli", run_name="__main__", alter_sys=False)
    assert exc.value.code == 0
