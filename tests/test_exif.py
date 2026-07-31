"""Tests for selective EXIF handling."""

from __future__ import annotations

from pathlib import Path

import piexif
import pytest
from PIL import Image
from typer.testing import CliRunner

from pixopt.cli import app
from pixopt.exif import EXIFGroup, apply_filtered_exif, filter_exif, get_exif_groups
from pixopt.optimizer import optimize_image


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_image_with_exif(
    output_dir: Path,
    name: str,
    size: tuple[int, int] = (100, 100),
    *,
    orientation: int = 3,
    copyright_str: str = "© 2025 Test",
    gps: bool = True,
    make: str = "TestCamera",
    model: str = "X1000",
    datetime: str = "2025:01:01 12:00:00",
) -> Path:
    """Create a JPEG image with known EXIF data."""
    path = output_dir / name
    img = Image.new("RGB", size, (128, 128, 128))
    buf = path.with_suffix(".buf.jpg")

    zeroth_ifd = {
        piexif.ImageIFD.Make: make.encode(),
        piexif.ImageIFD.Model: model.encode(),
        piexif.ImageIFD.DateTime: datetime.encode(),
        piexif.ImageIFD.Copyright: copyright_str.encode(),
        piexif.ImageIFD.Orientation: orientation,
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: datetime.encode(),
        piexif.ExifIFD.ExposureTime: (1, 125),
        piexif.ExifIFD.FNumber: (28, 10),
    }
    gps_ifd = {}
    if gps:
        gps_ifd = {
            piexif.GPSIFD.GPSVersionID: (2, 3, 0, 0),
            piexif.GPSIFD.GPSLatitude: ((40, 1), (25, 1), (0, 1)),
            piexif.GPSIFD.GPSLatitudeRef: b"N",
        }

    exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd}
    exif_bytes = piexif.dump(exif_dict)
    img.save(buf, "JPEG", quality=95, exif=exif_bytes)
    buf.rename(path)
    return path


# ---------------------------------------------------------------------------
# EXIFGroup enum tests
# ---------------------------------------------------------------------------


def test_exif_group_values() -> None:
    assert EXIFGroup.ORIENTATION.value == "orientation"
    assert EXIFGroup.COPYRIGHT.value == "copyright"
    assert EXIFGroup.GPS.value == "gps"
    assert EXIFGroup.CAMERA.value == "camera"
    assert EXIFGroup.DATE.value == "date"


def test_exif_group_from_string() -> None:
    assert EXIFGroup("orientation") == EXIFGroup.ORIENTATION
    assert EXIFGroup("gps") == EXIFGroup.GPS


# ---------------------------------------------------------------------------
# get_exif_groups tests
# ---------------------------------------------------------------------------


def test_get_exif_groups_full(output_dir: Path) -> None:
    path = _make_image_with_exif(output_dir, "full_exif.jpg")
    groups = get_exif_groups(path)
    assert EXIFGroup.CAMERA in groups
    assert EXIFGroup.COPYRIGHT in groups
    assert EXIFGroup.GPS in groups
    assert EXIFGroup.DATE in groups
    assert EXIFGroup.ORIENTATION in groups
    assert EXIFGroup.EXPOSURE in groups


def test_get_exif_groups_no_exif(output_dir: Path) -> None:
    path = output_dir / "no_exif.jpg"
    Image.new("RGB", (50, 50), (200, 200, 200)).save(path, "JPEG", quality=90)
    groups = get_exif_groups(path)
    assert len(groups) == 0


def test_get_exif_groups_corrupt_file(output_dir: Path) -> None:
    path = output_dir / "corrupt.jpg"
    path.write_bytes(b"not an image")
    groups = get_exif_groups(path)
    assert len(groups) == 0


# ---------------------------------------------------------------------------
# filter_exif tests
# ---------------------------------------------------------------------------


def test_filter_exif_keep_only_orientation(output_dir: Path) -> None:
    path = _make_image_with_exif(output_dir, "filter_orient.jpg")
    exif_dict = piexif.load(str(path))
    filtered = filter_exif(exif_dict, {EXIFGroup.ORIENTATION})

    assert piexif.ImageIFD.Orientation in filtered["0th"]
    assert piexif.ImageIFD.Copyright not in filtered["0th"]
    assert piexif.ImageIFD.Make not in filtered["0th"]
    assert filtered["GPS"] == {}


def test_filter_exif_keep_gps_and_camera(output_dir: Path) -> None:
    path = _make_image_with_exif(output_dir, "filter_gps_cam.jpg")
    exif_dict = piexif.load(str(path))
    filtered = filter_exif(exif_dict, {EXIFGroup.GPS, EXIFGroup.CAMERA})

    assert piexif.ImageIFD.Make in filtered["0th"]
    assert piexif.ImageIFD.Model in filtered["0th"]
    assert piexif.GPSIFD.GPSLatitude in filtered["GPS"]
    assert piexif.ImageIFD.Copyright not in filtered["0th"]
    assert piexif.ImageIFD.Orientation not in filtered["0th"]


def test_filter_exif_keep_none(output_dir: Path) -> None:
    path = _make_image_with_exif(output_dir, "filter_none.jpg")
    exif_dict = piexif.load(str(path))
    filtered = filter_exif(exif_dict, set())

    assert filtered["0th"] == {}
    assert filtered["Exif"] == {}
    assert filtered["GPS"] == {}


def test_filter_exif_keep_all(output_dir: Path) -> None:
    path = _make_image_with_exif(output_dir, "filter_all.jpg")
    exif_dict = piexif.load(str(path))
    all_groups = set(EXIFGroup)
    filtered = filter_exif(exif_dict, all_groups)

    assert piexif.ImageIFD.Make in filtered["0th"]
    assert piexif.ImageIFD.Copyright in filtered["0th"]
    assert piexif.ImageIFD.Orientation in filtered["0th"]
    assert piexif.GPSIFD.GPSLatitude in filtered["GPS"]


# ---------------------------------------------------------------------------
# apply_filtered_exif tests
# ---------------------------------------------------------------------------


def test_apply_filtered_exif_strip_all(output_dir: Path) -> None:
    path = _make_image_with_exif(output_dir, "apply_strip.jpg")
    result = apply_filtered_exif(path, set())
    assert result is True
    groups = get_exif_groups(path)
    assert len(groups) == 0


def test_apply_filtered_exif_keep_orientation(output_dir: Path) -> None:
    path = _make_image_with_exif(output_dir, "apply_orient.jpg")
    result = apply_filtered_exif(path, {EXIFGroup.ORIENTATION})
    assert result is True
    groups = get_exif_groups(path)
    assert EXIFGroup.ORIENTATION in groups
    assert EXIFGroup.GPS not in groups
    assert EXIFGroup.CAMERA not in groups


def test_apply_filtered_exif_keep_copyright_and_date(output_dir: Path) -> None:
    path = _make_image_with_exif(output_dir, "apply_copyright_date.jpg")
    result = apply_filtered_exif(path, {EXIFGroup.COPYRIGHT, EXIFGroup.DATE})
    assert result is True
    groups = get_exif_groups(path)
    assert EXIFGroup.COPYRIGHT in groups
    assert EXIFGroup.DATE in groups
    assert EXIFGroup.GPS not in groups
    assert EXIFGroup.CAMERA not in groups


def test_apply_filtered_exif_no_exif_image(output_dir: Path) -> None:
    path = output_dir / "apply_no_exif.jpg"
    Image.new("RGB", (50, 50), (200, 200, 200)).save(path, "JPEG", quality=90)
    # piexif.load succeeds on images without EXIF (returns empty dicts),
    # so apply_filtered_exif will attempt to process but find nothing to keep.
    _ = apply_filtered_exif(path, {EXIFGroup.ORIENTATION})
    # No EXIF groups should be present after.
    groups = get_exif_groups(path)
    assert EXIFGroup.ORIENTATION not in groups


# ---------------------------------------------------------------------------
# optimize_image with keep_exif_groups tests
# ---------------------------------------------------------------------------


def test_optimize_keep_exif_orientation(output_dir: Path) -> None:
    source = _make_image_with_exif(output_dir, "opt_keep_orient.jpg")
    output = output_dir / "opt_keep_orient_out.jpg"
    result = optimize_image(
        source,
        output,
        quality=80,
        strip_metadata=True,
        keep_exif_groups={EXIFGroup.ORIENTATION},
    )
    assert result.success
    groups = get_exif_groups(output)
    assert EXIFGroup.ORIENTATION in groups
    assert EXIFGroup.GPS not in groups
    assert EXIFGroup.CAMERA not in groups


def test_optimize_keep_exif_gps_and_camera(output_dir: Path) -> None:
    source = _make_image_with_exif(output_dir, "opt_keep_gps_cam.jpg")
    output = output_dir / "opt_keep_gps_cam_out.jpg"
    result = optimize_image(
        source,
        output,
        quality=80,
        strip_metadata=True,
        keep_exif_groups={EXIFGroup.GPS, EXIFGroup.CAMERA},
    )
    assert result.success
    groups = get_exif_groups(output)
    assert EXIFGroup.GPS in groups
    assert EXIFGroup.CAMERA in groups
    assert EXIFGroup.COPYRIGHT not in groups


def test_optimize_strip_all_exif(output_dir: Path) -> None:
    source = _make_image_with_exif(output_dir, "opt_strip_all.jpg")
    output = output_dir / "opt_strip_all_out.jpg"
    result = optimize_image(
        source,
        output,
        quality=80,
        strip_metadata=True,
    )
    assert result.success
    groups = get_exif_groups(output)
    assert len(groups) == 0


def test_optimize_keep_exif_all_groups(output_dir: Path) -> None:
    source = _make_image_with_exif(output_dir, "opt_keep_all.jpg")
    output = output_dir / "opt_keep_all_out.jpg"
    result = optimize_image(
        source,
        output,
        quality=80,
        strip_metadata=True,
        keep_exif_groups=set(EXIFGroup),
    )
    assert result.success
    groups = get_exif_groups(output)
    assert EXIFGroup.CAMERA in groups
    assert EXIFGroup.COPYRIGHT in groups
    assert EXIFGroup.GPS in groups


# ---------------------------------------------------------------------------
# CLI --keep-exif tests
# ---------------------------------------------------------------------------


def test_cli_optimize_keep_exif(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_image_with_exif(output_dir, "cli_keep.jpg")
    output = output_dir / "cli_keep_out.jpg"
    result = runner.invoke(
        app,
        [
            "optimize",
            str(source),
            str(output),
            "--keep-exif",
            "orientation",
            "--keep-exif",
            "copyright",
        ],
    )
    assert result.exit_code == 0
    groups = get_exif_groups(output)
    assert EXIFGroup.ORIENTATION in groups
    assert EXIFGroup.COPYRIGHT in groups
    assert EXIFGroup.GPS not in groups


def test_cli_optimize_strip_all_no_keep_exif(output_dir: Path) -> None:
    runner = CliRunner()
    source = _make_image_with_exif(output_dir, "cli_strip.jpg")
    output = output_dir / "cli_strip_out.jpg"
    result = runner.invoke(
        app,
        ["optimize", str(source), str(output)],
    )
    assert result.exit_code == 0
    groups = get_exif_groups(output)
    assert len(groups) == 0
