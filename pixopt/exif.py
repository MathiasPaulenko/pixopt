"""Selective EXIF handling.

Allows keeping or stripping specific EXIF groups (orientation, copyright,
GPS, camera, etc.) instead of the current all-or-nothing approach.
"""

from __future__ import annotations

import contextlib
from enum import Enum
from pathlib import Path
from typing import Any

__all__ = ["EXIFGroup", "apply_filtered_exif", "filter_exif", "get_exif_groups"]


class EXIFGroup(str, Enum):
    """Logical EXIF group categories for selective keep/strip."""

    ORIENTATION = "orientation"
    COPYRIGHT = "copyright"
    GPS = "gps"
    CAMERA = "camera"
    LENS = "lens"
    EXPOSURE = "exposure"
    DATE = "date"
    SOFTWARE = "software"
    THUMBNAIL = "thumbnail"


def _build_group_tag_map() -> dict[EXIFGroup, list[tuple[str, set[int]]]]:
    """Build mapping from EXIFGroup to (IFD name, set of piexif tag IDs)."""
    import piexif

    return {
        EXIFGroup.ORIENTATION: [("0th", {piexif.ImageIFD.Orientation})],
        EXIFGroup.COPYRIGHT: [("0th", {piexif.ImageIFD.Copyright})],
        EXIFGroup.GPS: [("GPS", set())],  # All GPS tags
        EXIFGroup.CAMERA: [("0th", {piexif.ImageIFD.Make, piexif.ImageIFD.Model})],
        EXIFGroup.LENS: [("Exif", {piexif.ExifIFD.LensModel, piexif.ExifIFD.LensSpecification})],
        EXIFGroup.EXPOSURE: [
            (
                "Exif",
                {
                    piexif.ExifIFD.ExposureTime,
                    piexif.ExifIFD.FNumber,
                    piexif.ExifIFD.ISOSpeedRatings,
                    piexif.ExifIFD.ExposureBiasValue,
                },
            ),
        ],
        EXIFGroup.DATE: [
            ("0th", {piexif.ImageIFD.DateTime}),
            ("Exif", {piexif.ExifIFD.DateTimeOriginal, piexif.ExifIFD.DateTimeDigitized}),
        ],
        EXIFGroup.SOFTWARE: [("0th", {piexif.ImageIFD.Software})],
        EXIFGroup.THUMBNAIL: [("1st", set())],  # Special: thumbnail IFD
    }


def get_exif_groups(path: Path | str) -> set[EXIFGroup]:
    """Return the set of EXIF groups present in an image.

    Args:
        path: Path to the image file.

    Returns:
        A set of :class:`EXIFGroup` values found in the image's EXIF data.
    """
    import piexif

    p = Path(path)
    try:
        exif_dict = piexif.load(str(p))
    except (OSError, ValueError):
        return set()

    group_map = _build_group_tag_map()
    found: set[EXIFGroup] = set()

    for group, tags in group_map.items():
        for ifd_name, tag_ids in tags:
            ifd = exif_dict.get(ifd_name, {})
            if ifd_name == "1st":
                if exif_dict.get("thumbnail"):
                    found.add(group)
                continue
            if not tag_ids:
                if ifd:
                    found.add(group)
            else:
                if any(tag in ifd for tag in tag_ids):
                    found.add(group)

    return found


def filter_exif(
    exif_dict: dict[str, Any],
    keep_groups: set[EXIFGroup],
) -> dict[str, Any]:
    """Filter an EXIF dict (from piexif.load) to only keep specified groups.

    Args:
        exif_dict: EXIF dict as returned by ``piexif.load``.
        keep_groups: Set of EXIF groups to retain. All others are stripped.

    Returns:
        A new EXIF dict with only the specified groups retained.
    """
    group_map = _build_group_tag_map()

    filtered: dict[str, Any] = {
        "0th": {},
        "Exif": {},
        "GPS": {},
        "1st": {},
        "Interoperability": {},
        "thumbnail": None,
    }

    for group, tags in group_map.items():
        if group not in keep_groups:
            continue
        for ifd_name, tag_ids in tags:
            ifd = exif_dict.get(ifd_name, {})
            if ifd_name == "1st":
                if exif_dict.get("thumbnail"):
                    filtered["thumbnail"] = exif_dict["thumbnail"]
                continue
            if not tag_ids:
                filtered[ifd_name].update(ifd)
            else:
                for tag in tag_ids:
                    if tag in ifd:
                        filtered[ifd_name][tag] = ifd[tag]

    return filtered


def apply_filtered_exif(
    path: Path | str,
    keep_groups: set[EXIFGroup],
) -> bool:
    """Remove EXIF groups not in ``keep_groups`` from a saved image.

    Args:
        path: Path to the image file (JPEG or WEBP).
        keep_groups: EXIF groups to retain. Empty set = strip all.

    Returns:
        True if EXIF was modified, False otherwise.
    """
    import piexif

    p = Path(path)

    try:
        exif_dict = piexif.load(str(p))
    except (OSError, ValueError):
        return False

    if not keep_groups:
        try:
            piexif.remove(str(p))
            return True
        except (OSError, ValueError):
            return False

    filtered = filter_exif(exif_dict, keep_groups)

    has_data = any(
        filtered.get(ifd) for ifd in ("0th", "Exif", "GPS", "1st", "Interoperability")
    ) or filtered.get("thumbnail")

    if not has_data:
        with contextlib.suppress(OSError, ValueError):
            piexif.remove(str(p))
        return True

    try:
        exif_bytes = piexif.dump(filtered)
        piexif.insert(exif_bytes, str(p))
        return True
    except (OSError, ValueError):
        return False
