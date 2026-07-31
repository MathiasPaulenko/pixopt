"""Tests for progress callbacks."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from pixopt.optimizer import batch_optimize, optimize_directory
from pixopt.progress import ProgressCallback, ProgressInfo


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_image(output_dir: Path, name: str, size: tuple[int, int] = (50, 50)) -> Path:
    path = output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (128, 128, 128)).save(path, "JPEG", quality=90)
    return path


# ---------------------------------------------------------------------------
# ProgressInfo dataclass tests
# ---------------------------------------------------------------------------


def test_progress_info_basic() -> None:
    info = ProgressInfo(current=3, total=10, current_file=Path("test.jpg"), success=True)
    assert info.current == 3
    assert info.total == 10
    assert info.success is True
    assert info.message == ""


def test_progress_info_percent() -> None:
    info = ProgressInfo(current=5, total=10, current_file=Path("test.jpg"), success=True)
    assert info.percent == 50.0


def test_progress_info_percent_zero_total() -> None:
    info = ProgressInfo(current=0, total=0, current_file=Path("test.jpg"), success=True)
    assert info.percent == 100.0


def test_progress_info_is_done() -> None:
    info = ProgressInfo(current=10, total=10, current_file=Path("test.jpg"), success=True)
    assert info.is_done is True


def test_progress_info_not_done() -> None:
    info = ProgressInfo(current=5, total=10, current_file=Path("test.jpg"), success=True)
    assert info.is_done is False


def test_progress_info_with_message() -> None:
    info = ProgressInfo(
        current=2, total=5, current_file=Path("bad.jpg"), success=False, message="File error"
    )
    assert info.success is False
    assert info.message == "File error"


# ---------------------------------------------------------------------------
# ProgressCallback protocol test
# ---------------------------------------------------------------------------


def test_progress_callback_protocol() -> None:
    def my_callback(info: ProgressInfo) -> None:
        pass

    assert isinstance(my_callback, ProgressCallback)


def test_non_callable_not_progress_callback() -> None:
    assert not isinstance(42, ProgressCallback)


# ---------------------------------------------------------------------------
# batch_optimize with on_progress tests
# ---------------------------------------------------------------------------


def test_batch_optimize_callback_called(output_dir: Path) -> None:
    sources = [_make_image(output_dir, f"batch_{i}.jpg") for i in range(3)]
    out_dir = output_dir / "batch_out"
    out_dir.mkdir(exist_ok=True)

    calls: list[ProgressInfo] = []

    def on_progress(info: ProgressInfo) -> None:
        calls.append(info)

    report = batch_optimize(sources, out_dir, on_progress=on_progress)

    assert len(calls) == 3
    assert report.total_files == 3
    for i, call in enumerate(calls, 1):
        assert call.current == i
        assert call.total == 3
        assert call.success is True


def test_batch_optimize_callback_order(output_dir: Path) -> None:
    sources = [_make_image(output_dir, f"order_{i}.jpg") for i in range(4)]
    out_dir = output_dir / "order_out"
    out_dir.mkdir(exist_ok=True)

    current_values: list[int] = []

    def on_progress(info: ProgressInfo) -> None:
        current_values.append(info.current)

    batch_optimize(sources, out_dir, on_progress=on_progress)

    assert current_values == [1, 2, 3, 4]


def test_batch_optimize_callback_is_done_at_end(output_dir: Path) -> None:
    sources = [_make_image(output_dir, f"done_{i}.jpg") for i in range(2)]
    out_dir = output_dir / "done_out"
    out_dir.mkdir(exist_ok=True)

    last_info: ProgressInfo | None = None

    def on_progress(info: ProgressInfo) -> None:
        nonlocal last_info
        last_info = info

    batch_optimize(sources, out_dir, on_progress=on_progress)

    assert last_info is not None
    assert last_info.is_done is True


def test_batch_optimize_no_callback(output_dir: Path) -> None:
    sources = [_make_image(output_dir, "nocb_0.jpg"), _make_image(output_dir, "nocb_1.jpg")]
    out_dir = output_dir / "nocb_out"
    out_dir.mkdir(exist_ok=True)

    report = batch_optimize(sources, out_dir)
    assert report.total_files == 2
    assert report.succeeded == 2


def test_batch_optimize_callback_with_failure(output_dir: Path) -> None:
    good = _make_image(output_dir, "fail_good.jpg")
    bad = Path(output_dir) / "nonexistent.jpg"
    out_dir = output_dir / "fail_out"
    out_dir.mkdir(exist_ok=True)

    calls: list[ProgressInfo] = []

    def on_progress(info: ProgressInfo) -> None:
        calls.append(info)

    report = batch_optimize([good, bad], out_dir, on_progress=on_progress)

    assert len(calls) == 2
    assert calls[0].success is True
    assert calls[1].success is False
    assert calls[1].message != ""
    assert report.failed == 1


# ---------------------------------------------------------------------------
# optimize_directory with on_progress tests
# ---------------------------------------------------------------------------


def test_optimize_directory_callback_called(output_dir: Path) -> None:
    src_dir = output_dir / "dir_src"
    src_dir.mkdir(exist_ok=True)
    for i in range(3):
        Image.new("RGB", (50, 50), (100, 100, 100)).save(
            src_dir / f"img_{i}.jpg", "JPEG", quality=90
        )

    out_dir = output_dir / "dir_out"
    out_dir.mkdir(exist_ok=True)

    calls: list[ProgressInfo] = []

    def on_progress(info: ProgressInfo) -> None:
        calls.append(info)

    results = optimize_directory(src_dir, out_dir, on_progress=on_progress)

    assert len(results) == 3
    assert len(calls) == 3
    for i, call in enumerate(calls, 1):
        assert call.current == i
        assert call.total == 3
        assert call.success is True


def test_optimize_directory_callback_is_done(output_dir: Path) -> None:
    src_dir = output_dir / "dir_done_src"
    src_dir.mkdir(exist_ok=True)
    for i in range(2):
        Image.new("RGB", (50, 50), (100, 100, 100)).save(
            src_dir / f"img_{i}.jpg", "JPEG", quality=90
        )

    out_dir = output_dir / "dir_done_out"
    out_dir.mkdir(exist_ok=True)

    last_info: ProgressInfo | None = None

    def on_progress(info: ProgressInfo) -> None:
        nonlocal last_info
        last_info = info

    optimize_directory(src_dir, out_dir, on_progress=on_progress)

    assert last_info is not None
    assert last_info.is_done is True


def test_optimize_directory_no_callback(output_dir: Path) -> None:
    src_dir = output_dir / "dir_nocb_src"
    src_dir.mkdir(exist_ok=True)
    for i in range(2):
        Image.new("RGB", (50, 50), (100, 100, 100)).save(
            src_dir / f"img_{i}.jpg", "JPEG", quality=90
        )

    out_dir = output_dir / "dir_nocb_out"
    out_dir.mkdir(exist_ok=True)

    results = optimize_directory(src_dir, out_dir)
    assert len(results) == 2


def test_optimize_directory_empty_dir(output_dir: Path) -> None:
    src_dir = output_dir / "dir_empty"
    src_dir.mkdir(exist_ok=True)
    out_dir = output_dir / "dir_empty_out"
    out_dir.mkdir(exist_ok=True)

    calls: list[ProgressInfo] = []

    def on_progress(info: ProgressInfo) -> None:
        calls.append(info)

    results = optimize_directory(src_dir, out_dir, on_progress=on_progress)

    assert len(results) == 0
    assert len(calls) == 0
