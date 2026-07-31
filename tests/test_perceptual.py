"""Tests for perceptual hashing and duplicate detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli.app import app
from pixopt.perceptual import (
    DuplicateReport,
    HashResult,
    ahash,
    compute_hash,
    dhash,
    find_duplicates,
    hamming_distance,
    phash,
    scan_duplicates,
)

runner = CliRunner()


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
    fmt: str = "JPEG",
) -> Path:
    path = output_dir / "data" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, fmt, quality=90)
    return path


def _make_gradient(output_dir: Path, name: str, size: tuple[int, int] = (200, 200)) -> Path:
    path = output_dir / "data" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size)
    pixels = img.load()
    assert pixels is not None
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = ((x * 255) // size[0], (y * 255) // size[1], 128)
    img.save(path, "JPEG", quality=90)
    return path


# ---------------------------------------------------------------------------
# Hash function tests
# ---------------------------------------------------------------------------


def test_ahash_returns_hex_string(output_dir: Path) -> None:
    path = _make_image(output_dir, "a.jpg")
    h = ahash(path)
    assert isinstance(h, str)
    assert all(c in "0123456789abcdef" for c in h)


def test_dhash_returns_hex_string(output_dir: Path) -> None:
    path = _make_image(output_dir, "a.jpg")
    h = dhash(path)
    assert isinstance(h, str)
    assert all(c in "0123456789abcdef" for c in h)


def test_phash_returns_hex_string(output_dir: Path) -> None:
    path = _make_image(output_dir, "a.jpg")
    h = phash(path)
    assert isinstance(h, str)
    assert all(c in "0123456789abcdef" for c in h)


def test_ahash_identical_images_same_hash(output_dir: Path) -> None:
    path1 = _make_image(output_dir, "same1.jpg", color=(100, 150, 200))
    path2 = _make_image(output_dir, "same2.jpg", color=(100, 150, 200))
    assert ahash(path1) == ahash(path2)


def test_dhash_identical_images_same_hash(output_dir: Path) -> None:
    path1 = _make_image(output_dir, "same1.jpg", color=(100, 150, 200))
    path2 = _make_image(output_dir, "same2.jpg", color=(100, 150, 200))
    assert dhash(path1) == dhash(path2)


def test_phash_identical_images_same_hash(output_dir: Path) -> None:
    path1 = _make_image(output_dir, "same1.jpg", color=(100, 150, 200))
    path2 = _make_image(output_dir, "same2.jpg", color=(100, 150, 200))
    assert phash(path1) == phash(path2)


def test_ahash_different_images_different_hash(output_dir: Path) -> None:
    path1 = _make_gradient(output_dir, "grad.jpg")
    path2 = _make_image(output_dir, "solid.jpg", color=(50, 50, 50))
    assert ahash(path1) != ahash(path2)


def test_dhash_different_images_different_hash(output_dir: Path) -> None:
    path1 = _make_gradient(output_dir, "grad.jpg")
    path2 = _make_image(output_dir, "solid.jpg", color=(50, 50, 50))
    assert dhash(path1) != dhash(path2)


def test_phash_different_images_different_hash(output_dir: Path) -> None:
    path1 = _make_gradient(output_dir, "grad.jpg")
    path2 = _make_image(output_dir, "solid.jpg", color=(50, 50, 50))
    assert phash(path1) != phash(path2)


def test_hash_size_affects_length(output_dir: Path) -> None:
    path = _make_image(output_dir, "a.jpg")
    h8 = ahash(path, hash_size=8)
    h16 = ahash(path, hash_size=16)
    assert len(h16) > len(h8)


def test_phash_highfreq_factor_invalid(output_dir: Path) -> None:
    path = _make_image(output_dir, "a.jpg")
    with pytest.raises(ValueError, match="highfreq_factor"):
        phash(path, highfreq_factor=17)


# ---------------------------------------------------------------------------
# compute_hash tests
# ---------------------------------------------------------------------------


def test_compute_hash_phash(output_dir: Path) -> None:
    path = _make_image(output_dir, "a.jpg")
    result = compute_hash(path, algorithm="phash")
    assert isinstance(result, HashResult)
    assert result.algorithm == "phash"
    assert result.file_path == path
    assert result.hash_hex


def test_compute_hash_dhash(output_dir: Path) -> None:
    path = _make_image(output_dir, "a.jpg")
    result = compute_hash(path, algorithm="dhash")
    assert result.algorithm == "dhash"


def test_compute_hash_ahash(output_dir: Path) -> None:
    path = _make_image(output_dir, "a.jpg")
    result = compute_hash(path, algorithm="ahash")
    assert result.algorithm == "ahash"


def test_compute_hash_invalid_algorithm(output_dir: Path) -> None:
    path = _make_image(output_dir, "a.jpg")
    with pytest.raises(ValueError, match="Unknown hash algorithm"):
        compute_hash(path, algorithm="invalid")


def test_hash_result_to_dict(output_dir: Path) -> None:
    path = _make_image(output_dir, "a.jpg")
    result = compute_hash(path, algorithm="phash")
    d = result.to_dict()
    assert d["algorithm"] == "phash"
    assert d["file_path"] == str(path)
    json.dumps(d)


# ---------------------------------------------------------------------------
# hamming_distance tests
# ---------------------------------------------------------------------------


def test_hamming_distance_identical() -> None:
    assert hamming_distance("ffff", "ffff") == 0


def test_hamming_distance_different() -> None:
    assert hamming_distance("0000", "ffff") == 16


def test_hamming_distance_one_bit() -> None:
    assert hamming_distance("0001", "0000") == 1


def test_hamming_distance_different_lengths() -> None:
    # Should pad shorter with zeros
    dist = hamming_distance("ff", "ffff")
    assert dist == 8


# ---------------------------------------------------------------------------
# find_duplicates tests
# ---------------------------------------------------------------------------


def test_find_duplicates_identical_images(output_dir: Path) -> None:
    path1 = _make_image(output_dir, "dup1.jpg", color=(100, 150, 200))
    path2 = _make_image(output_dir, "dup2.jpg", color=(100, 150, 200))
    path3 = _make_gradient(output_dir, "unique.jpg")

    hashes = [
        compute_hash(path1, algorithm="ahash"),
        compute_hash(path2, algorithm="ahash"),
        compute_hash(path3, algorithm="ahash"),
    ]
    groups = find_duplicates(hashes, threshold=0)

    assert len(groups) == 1
    assert groups[0].count == 2
    assert path1 in groups[0].files
    assert path2 in groups[0].files
    assert path3 not in groups[0].files


def test_find_duplicates_no_duplicates(output_dir: Path) -> None:
    path1 = _make_gradient(output_dir, "grad1.jpg")
    path2 = _make_image(output_dir, "solid.jpg", color=(50, 50, 50))

    hashes = [
        compute_hash(path1, algorithm="ahash"),
        compute_hash(path2, algorithm="ahash"),
    ]
    groups = find_duplicates(hashes, threshold=0)
    assert groups == []


def test_find_duplicates_empty_list() -> None:
    groups = find_duplicates([])
    assert groups == []


def test_find_duplicates_threshold_allows_near(output_dir: Path) -> None:
    path1 = _make_image(output_dir, "a.jpg", color=(100, 100, 100))
    path2 = _make_image(output_dir, "b.jpg", color=(110, 110, 110))

    hashes = [
        compute_hash(path1, algorithm="ahash"),
        compute_hash(path2, algorithm="ahash"),
    ]
    # With high threshold, near-duplicates should be found
    groups = find_duplicates(hashes, threshold=64)
    assert len(groups) >= 1


def test_duplicate_group_to_dict(output_dir: Path) -> None:
    path1 = _make_image(output_dir, "dup1.jpg", color=(100, 150, 200))
    path2 = _make_image(output_dir, "dup2.jpg", color=(100, 150, 200))

    hashes = [
        compute_hash(path1, algorithm="ahash"),
        compute_hash(path2, algorithm="ahash"),
    ]
    groups = find_duplicates(hashes, threshold=0)
    d = groups[0].to_dict()
    assert d["count"] == 2
    assert len(d["files"]) == 2
    json.dumps(d)


# ---------------------------------------------------------------------------
# scan_duplicates tests
# ---------------------------------------------------------------------------


def test_scan_duplicates_finds_identical(output_dir: Path) -> None:
    _make_image(output_dir, "dup1.jpg", color=(100, 150, 200))
    _make_image(output_dir, "dup2.jpg", color=(100, 150, 200))
    _make_gradient(output_dir, "unique.jpg")

    report = scan_duplicates(output_dir / "data", algorithm="ahash", threshold=0)

    assert isinstance(report, DuplicateReport)
    assert report.total_files == 3
    assert len(report.duplicate_groups) == 1
    assert report.has_duplicates
    assert report.total_duplicates == 2


def test_scan_duplicates_no_duplicates(output_dir: Path) -> None:
    _make_gradient(output_dir, "a.jpg")
    _make_image(output_dir, "b.jpg", color=(50, 50, 50))

    report = scan_duplicates(output_dir / "data", algorithm="ahash", threshold=0)

    assert not report.has_duplicates
    assert report.duplicate_groups == []


def test_scan_duplicates_nonexistent_directory(output_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        scan_duplicates(output_dir / "nonexistent")


def test_perceptual_hash_input_too_large(output_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pixopt.image_ops.MAX_INPUT_BYTES", 10)
    path = output_dir / "data" / "huge.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * 11)
    with pytest.raises(ValueError, match="too large"):
        ahash(path)


def test_scan_duplicates_empty_directory(output_dir: Path) -> None:
    empty = output_dir / "empty"
    empty.mkdir(parents=True, exist_ok=True)
    report = scan_duplicates(empty)

    assert report.total_files == 0
    assert not report.has_duplicates


def test_find_duplicates_too_many_near_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pixopt.perceptual.MAX_NEAR_DUPLICATE_SCAN", 2)
    hashes = [
        HashResult(algorithm="ahash", hash_hex="0" * 16, file_path=Path(f"{i}.jpg"), hash_size=8)
        for i in range(3)
    ]
    with pytest.raises(ValueError, match="Too many"):
        find_duplicates(hashes, threshold=1)


def test_scan_duplicates_too_many(output_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pixopt.perceptual.MAX_NEAR_DUPLICATE_SCAN", 1)
    _make_image(output_dir, "a.jpg", color=(100, 150, 200))
    _make_image(output_dir, "b.jpg", color=(50, 50, 50))
    report = scan_duplicates(output_dir / "data", threshold=1)
    assert report.total_files <= 1


def test_scan_duplicates_with_phash(output_dir: Path) -> None:
    _make_image(output_dir, "dup1.jpg", color=(100, 150, 200))
    _make_image(output_dir, "dup2.jpg", color=(100, 150, 200))

    report = scan_duplicates(output_dir / "data", algorithm="phash", threshold=0)
    assert len(report.duplicate_groups) == 1


def test_scan_duplicates_with_dhash(output_dir: Path) -> None:
    _make_image(output_dir, "dup1.jpg", color=(100, 150, 200))
    _make_image(output_dir, "dup2.jpg", color=(100, 150, 200))

    report = scan_duplicates(output_dir / "data", algorithm="dhash", threshold=0)
    assert len(report.duplicate_groups) == 1


def test_scan_duplicates_report_to_dict(output_dir: Path) -> None:
    _make_image(output_dir, "dup1.jpg", color=(100, 150, 200))
    _make_image(output_dir, "dup2.jpg", color=(100, 150, 200))

    report = scan_duplicates(output_dir / "data", algorithm="ahash", threshold=0)
    d = report.to_dict()
    assert d["algorithm"] == "ahash"
    assert isinstance(d["duplicate_groups"], list)
    json.dumps(d)


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_duplicates_basic(output_dir: Path) -> None:
    _make_image(output_dir, "dup1.jpg", color=(100, 150, 200))
    _make_image(output_dir, "dup2.jpg", color=(100, 150, 200))
    _make_gradient(output_dir, "unique.jpg")

    result = runner.invoke(
        app, ["duplicates", str(output_dir / "data"), "--algorithm", "ahash", "--threshold", "0"]
    )

    assert result.exit_code == 0
    assert "dup1.jpg" in result.output
    assert "dup2.jpg" in result.output


def test_cli_duplicates_json_output(output_dir: Path) -> None:
    _make_image(output_dir, "dup1.jpg", color=(100, 150, 200))
    _make_image(output_dir, "dup2.jpg", color=(100, 150, 200))

    result = runner.invoke(
        app,
        [
            "duplicates",
            str(output_dir / "data"),
            "--algorithm",
            "ahash",
            "--threshold",
            "0",
            "--json",
        ],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.stdout.strip())
    assert parsed["total_files"] == 2
    assert len(parsed["duplicate_groups"]) == 1


def test_cli_duplicates_no_duplicates(output_dir: Path) -> None:
    _make_gradient(output_dir, "a.jpg")
    _make_image(output_dir, "b.jpg", color=(50, 50, 50))

    result = runner.invoke(
        app, ["duplicates", str(output_dir / "data"), "--algorithm", "ahash", "--threshold", "0"]
    )

    assert result.exit_code == 0
    assert "No duplicates" in result.output


def test_cli_duplicates_nonexistent_directory(output_dir: Path) -> None:
    result = runner.invoke(app, ["duplicates", str(output_dir / "nope")])

    assert result.exit_code != 0
