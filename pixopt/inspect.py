"""Structured image metadata inspection.

Provides :func:`inspect_image` which returns a :class:`~pixopt.models.ImageInfo`
dataclass with dimensions, mode, format, DPI, alpha, animation info, EXIF,
ICC profile and orientation.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import Base

from pixopt.image_ops import _open_image
from pixopt.models import ImageInfo

__all__ = ["inspect_image"]

# Pre-compute the set of known EXIF tag IDs for fast lookup.
_EXIF_TAG_IDS = {t.value for t in Base}

# EXIF Orientation tag ID (0x0112).
_ORIENTATION_TAG = 0x0112


def inspect_image(source: Path | str) -> ImageInfo:
    """Inspect an image file and return structured metadata.

    Args:
        source: Path to the image file to inspect.

    Returns:
        An :class:`ImageInfo` dataclass with all detected metadata.

    Raises:
        FileNotFoundError: If *source* does not exist.
        UnidentifiedImageError: If the file is not a valid image.

    """
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    try:
        with _open_image(path, label="source") as img:
            img.load()

            # Basic properties.
            width, height = img.size
            mode = img.mode
            fmt = img.format or "UNKNOWN"
            file_size = path.stat().st_size

            # DPI (may be absent).
            dpi = img.info.get("dpi")
            if dpi is not None and isinstance(dpi, tuple) and len(dpi) == 2:
                dpi_tuple: tuple[float, float] | None = (float(dpi[0]), float(dpi[1]))
            else:
                dpi_tuple = None

            # Alpha channel detection.
            has_alpha = mode in ("RGBA", "LA") or (mode == "P" and "transparency" in img.info)

            # Animation / frame count.
            n_frames = 1
            with contextlib.suppress(AttributeError, OSError, ValueError):
                n_frames = getattr(img, "n_frames", 1)
            # Fallback: some Pillow versions need an explicit seek.
            if n_frames <= 1:
                try:
                    img.seek(1)
                    n_frames = getattr(img, "n_frames", 1)
                    img.seek(0)
                except (EOFError, AttributeError):
                    n_frames = 1
            is_animated = n_frames > 1
            frame_count = n_frames

            # EXIF data.
            exif_dict: dict[str, object] = {}
            orientation: int | None = None
            try:
                exif = img.getexif()
            except (AttributeError, OSError, ValueError, KeyError):
                exif = None

            if exif:
                for tag_id, value in exif.items():
                    tag_name = Base(tag_id).name if tag_id in _EXIF_TAG_IDS else f"Tag_{tag_id}"
                    # Convert bytes to a readable representation.
                    if isinstance(value, bytes):
                        value = value.hex()
                    exif_dict[tag_name] = value

                orientation = exif.get(_ORIENTATION_TAG)

            # ICC profile presence.
            icc_profile = "icc_profile" in img.info

            return ImageInfo(
                file_path=path,
                file_size=file_size,
                width=width,
                height=height,
                mode=mode,
                format=fmt,
                dpi=dpi_tuple,
                has_alpha=has_alpha,
                is_animated=is_animated,
                frame_count=frame_count,
                exif=exif_dict,
                icc_profile=icc_profile,
                orientation=orientation,
            )

    except UnidentifiedImageError:
        raise
    except FileNotFoundError:
        raise
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        msg = f"Error reading image {path}: {exc}"
        raise UnidentifiedImageError(msg) from exc
