"""Tests for async API."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

import pytest
from PIL import Image

from pixopt.async_api import (
    async_batch_optimize,
    async_inspect_image,
    async_optimize_base64,
    async_optimize_bytes,
    async_optimize_image,
    async_scan_directory,
    async_scan_duplicates,
)
from pixopt.models import BatchReport, ImageInfo, OptimizationResult, OutputFormat
from pixopt.progress import ProgressInfo


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
    Image.new("RGB", size, color).save(path, fmt)
    return path


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
# async_optimize_image
# ---------------------------------------------------------------------------


def test_async_optimize_image_basic(output_dir: Path) -> None:
    img = _make_image(output_dir, "source.png", (400, 300))
    out = output_dir / "optimized.webp"

    result = asyncio.run(
        async_optimize_image(img, out, output_format=OutputFormat.WEBP, quality=85)
    )

    assert isinstance(result, OptimizationResult)
    assert result.success
    assert out.exists()


def test_async_optimize_image_resize(output_dir: Path) -> None:
    img = _make_image(output_dir, "resize.png", (800, 600))
    out = output_dir / "resized.webp"

    result = asyncio.run(
        async_optimize_image(img, out, max_width=400, output_format=OutputFormat.WEBP)
    )

    assert result.success
    assert result.width == 400
    assert result.height == 300


def test_async_optimize_image_nonexistent(output_dir: Path) -> None:
    out = output_dir / "nope.webp"
    result = asyncio.run(async_optimize_image(output_dir / "nonexistent.png", out))

    assert not result.success


def test_async_optimize_image_is_coroutine(output_dir: Path) -> None:
    img = _make_image(output_dir, "coro.png")
    out = output_dir / "coro_out.webp"
    coro = async_optimize_image(img, out, output_format=OutputFormat.WEBP)
    assert asyncio.iscoroutine(coro)
    asyncio.run(coro)


# ---------------------------------------------------------------------------
# async_batch_optimize
# ---------------------------------------------------------------------------


def test_async_batch_optimize_basic(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"batch{i}.png", (300, 300)) for i in range(4)]
    out_dir = output_dir / "batch_out"

    result = asyncio.run(
        async_batch_optimize(imgs, out_dir, output_format=OutputFormat.WEBP, quality=85)
    )

    assert isinstance(result, BatchReport)
    assert result.total_files == 4
    assert result.succeeded == 4
    assert result.failed == 0


def test_async_batch_optimize_concurrency(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"conc{i}.png", (200, 200)) for i in range(6)]
    out_dir = output_dir / "conc_out"

    result = asyncio.run(
        async_batch_optimize(imgs, out_dir, max_concurrency=3, output_format=OutputFormat.WEBP)
    )

    assert result.total_files == 6
    assert result.succeeded == 6


def test_async_batch_optimize_with_failures(output_dir: Path) -> None:
    img1 = _make_image(output_dir, "ok.png")
    bad = output_dir / "bad.png"
    bad.write_bytes(b"not an image")
    out_dir = output_dir / "mixed_out"

    result = asyncio.run(
        async_batch_optimize([img1, bad], out_dir, output_format=OutputFormat.WEBP)
    )

    assert result.total_files == 2
    assert result.succeeded == 1
    assert result.failed == 1


def test_async_batch_optimize_progress_callback(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"prog{i}.png") for i in range(3)]
    out_dir = output_dir / "prog_out"
    progress_calls: list[tuple[int, int]] = []

    def on_progress(info: ProgressInfo) -> None:
        progress_calls.append((info.current, info.total))

    result = asyncio.run(
        async_batch_optimize(
            imgs, out_dir, output_format=OutputFormat.WEBP, on_progress=on_progress
        )
    )

    assert result.succeeded == 3
    assert len(progress_calls) == 3
    # All callbacks should have total=3, current values 1,2,3 (in any order)
    currents = sorted(c for c, t in progress_calls)
    assert currents == [1, 2, 3]
    assert all(t == 3 for _, t in progress_calls)


def test_async_batch_optimize_is_coroutine(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, "ic.png")]
    out_dir = output_dir / "ic_out"
    coro = async_batch_optimize(imgs, out_dir, output_format=OutputFormat.WEBP)
    assert asyncio.iscoroutine(coro)
    asyncio.run(coro)


def test_async_batch_optimize_empty_list(output_dir: Path) -> None:
    out_dir = output_dir / "empty_batch"
    result = asyncio.run(async_batch_optimize([], out_dir))

    assert result.total_files == 0
    assert result.succeeded == 0


def test_async_batch_optimize_invalid_max_concurrency(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, "bad_conc.png")]
    out_dir = output_dir / "bad_conc_out"
    with pytest.raises(ValueError, match="max_concurrency"):
        asyncio.run(async_batch_optimize(imgs, out_dir, max_concurrency=0))


def test_async_batch_optimize_progress_callback_error(output_dir: Path) -> None:
    imgs = [_make_image(output_dir, f"prog_err{i}.png") for i in range(2)]
    out_dir = output_dir / "prog_err_out"

    def on_progress(info: ProgressInfo) -> None:
        if info.current == 2:
            raise RuntimeError("callback failed")

    with pytest.raises(RuntimeError, match="callback failed"):
        asyncio.run(
            async_batch_optimize(
                imgs, out_dir, output_format=OutputFormat.WEBP, on_progress=on_progress
            )
        )


# ---------------------------------------------------------------------------
# async_inspect_image
# ---------------------------------------------------------------------------


def test_async_inspect_image_basic(output_dir: Path) -> None:
    img = _make_image(output_dir, "inspect.png", (250, 180))

    result = asyncio.run(async_inspect_image(img))

    assert isinstance(result, ImageInfo)
    assert result.width == 250
    assert result.height == 180


def test_async_inspect_image_is_coroutine(output_dir: Path) -> None:
    img = _make_image(output_dir, "ic_inspect.png")
    coro = async_inspect_image(img)
    assert asyncio.iscoroutine(coro)
    asyncio.run(coro)


# ---------------------------------------------------------------------------
# async_scan_directory
# ---------------------------------------------------------------------------


def test_async_scan_directory_basic(output_dir: Path) -> None:
    _make_image(output_dir, "scan1.png")
    _make_image(output_dir, "scan2.png")

    result = asyncio.run(async_scan_directory(output_dir))

    assert result.total_files == 2
    assert result.valid_images == 2


def test_async_scan_directory_is_coroutine(output_dir: Path) -> None:
    coro = async_scan_directory(output_dir)
    assert asyncio.iscoroutine(coro)
    asyncio.run(coro)


# ---------------------------------------------------------------------------
# async_scan_duplicates
# ---------------------------------------------------------------------------


def test_async_scan_duplicates_basic(output_dir: Path) -> None:
    _make_image(output_dir, "dup1.png", color=(100, 150, 200))
    _make_image(output_dir, "dup2.png", color=(100, 150, 200))
    _make_image(output_dir, "unique.png", color=(10, 20, 30))

    result = asyncio.run(async_scan_duplicates(output_dir, algorithm="ahash", threshold=0))

    assert result.total_files == 3
    assert len(result.duplicate_groups) == 1


def test_async_scan_duplicates_is_coroutine(output_dir: Path) -> None:
    coro = async_scan_duplicates(output_dir)
    assert asyncio.iscoroutine(coro)
    asyncio.run(coro)


# ---------------------------------------------------------------------------
# async_optimize_bytes
# ---------------------------------------------------------------------------


def test_async_optimize_bytes_basic() -> None:
    data = _make_gradient_bytes(size=(200, 200))

    result = asyncio.run(async_optimize_bytes(data, output_format=OutputFormat.WEBP, quality=85))

    assert result.success
    assert result.format == "WEBP"
    assert len(result.data) > 0


def test_async_optimize_bytes_resize() -> None:
    data = _make_gradient_bytes(size=(800, 600))

    result = asyncio.run(async_optimize_bytes(data, max_width=400, output_format=OutputFormat.WEBP))

    assert result.success
    assert result.width == 400
    assert result.height == 300


def test_async_optimize_bytes_is_coroutine() -> None:
    data = _make_gradient_bytes()
    coro = async_optimize_bytes(data, output_format=OutputFormat.WEBP)
    assert asyncio.iscoroutine(coro)
    asyncio.run(coro)


# ---------------------------------------------------------------------------
# async_optimize_base64
# ---------------------------------------------------------------------------


def test_async_optimize_base64_basic() -> None:
    import base64

    data = _make_gradient_bytes(size=(200, 200))
    b64_str = base64.b64encode(data).decode("ascii")

    result = asyncio.run(
        async_optimize_base64(b64_str, output_format=OutputFormat.WEBP, quality=85)
    )

    assert result.success is True
    assert result.base64 is not None
    assert result.format == "WEBP"


def test_async_optimize_base64_is_coroutine() -> None:
    import base64

    data = _make_gradient_bytes()
    b64_str = base64.b64encode(data).decode("ascii")
    coro = async_optimize_base64(b64_str, output_format=OutputFormat.WEBP)
    assert asyncio.iscoroutine(coro)
    asyncio.run(coro)


# ---------------------------------------------------------------------------
# Concurrent execution test
# ---------------------------------------------------------------------------


def test_concurrent_optimize_image(output_dir: Path) -> None:
    """Multiple async_optimize_image calls should run concurrently."""
    imgs = [_make_image(output_dir, f"concurrent{i}.png", (300, 300)) for i in range(4)]
    outputs = [output_dir / f"concurrent_out{i}.webp" for i in range(4)]

    async def run_all() -> list[OptimizationResult]:
        tasks = [
            async_optimize_image(img, out, output_format=OutputFormat.WEBP, quality=85)
            for img, out in zip(imgs, outputs, strict=True)
        ]
        return await asyncio.gather(*tasks)

    results = asyncio.run(run_all())

    assert len(results) == 4
    assert all(r.success for r in results)
    assert all(out.exists() for out in outputs)
