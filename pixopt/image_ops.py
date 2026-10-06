"""Low-level image manipulation operations."""

from __future__ import annotations

import contextlib
import io
import os
import re
import warnings
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import piexif
from PIL import Image, ImageOps
from PIL.Image import Resampling

from pixopt._units import MAX_IMAGE_DIMENSION, MAX_INPUT_BYTES, WHITE
from pixopt.utils import validate_no_parent_references

__all__ = [
    "apply_exif_orientation",
    "build_save_kwargs",
    "convert_mode",
    "parse_aspect_ratio",
    "parse_color",
    "resize_image",
    "resolve_and_adjust_path",
    "strip_exif_post_process",
    "strip_metadata_pillow",
]
from pixopt.format_resolver import resolve_output_format
from pixopt.models import Anchor, FitMode, OutputFormat


@contextmanager
def _open_image(path: Path | str, *, label: str = "source") -> Iterator[Image.Image]:
    """Open an image with size, dimension, path-traversal and decompression-bomb guards."""
    source_path = Path(path)
    if error := validate_no_parent_references(source_path, label):
        raise ValueError(error)
    fp: io.BufferedReader | None = None
    try:
        fp = source_path.open("rb")
        if os.fstat(fp.fileno()).st_size > MAX_INPUT_BYTES:
            raise ValueError(f"Input too large (max {MAX_INPUT_BYTES} bytes)")
        with Image.open(fp) as img:
            img.load()
            if img.width > MAX_IMAGE_DIMENSION or img.height > MAX_IMAGE_DIMENSION:
                raise ValueError(
                    f"Image dimensions too large: {img.width}x{img.height} "
                    f"(max {MAX_IMAGE_DIMENSION})"
                )
            yield img
    except Image.DecompressionBombError as exc:
        raise ValueError(f"Image too large or possible decompression bomb: {exc}") from exc
    finally:
        if fp is not None:
            fp.close()


def convert_mode(img: Image.Image, pillow_fmt: str) -> Image.Image:
    """Convert image mode so it can be saved in the requested format."""
    if pillow_fmt == "PNG":
        return img

    if pillow_fmt not in ("JPEG", "WEBP"):
        return img

    # JPEG and WEBP do not support alpha. Flatten any transparent image onto a
    # white background so the transparent areas are not replaced with an
    # unexpected color (Pillow's default is black when dropping alpha).
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, WHITE)
        channels = img.split()
        if img.mode == "RGBA" and len(channels) >= 4:
            background.paste(img, mask=channels[3])
        elif img.mode == "LA" and len(channels) >= 2:
            background.paste(img, mask=channels[1])
        else:
            raise ValueError(f"{img.mode} image has unexpected channel count: {len(channels)}")
        return background

    if img.mode == "P" and "transparency" in img.info:
        rgb = img.convert("RGBA")
        channels = rgb.split()
        if len(channels) < 4:
            raise ValueError(
                f"P/transparent image produced unexpected channel count: {len(channels)}"
            )
        background = Image.new("RGB", img.size, WHITE)
        background.paste(rgb, mask=channels[3])
        rgb.close()
        return background

    if img.mode == "RGB":
        return img

    return img.convert("RGB")


def apply_exif_orientation(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation and return a new image.

    Uses Pillow's ImageOps.exif_transpose, which rotates/flips the image
    according to the Orientation tag and removes the tag so the image is
    stored in its correct visual orientation.
    """
    return ImageOps.exif_transpose(img)


def parse_aspect_ratio(aspect_ratio: tuple[int, int] | str | None) -> tuple[int, int] | None:
    """Parse an aspect ratio into a (width, height) tuple."""
    if aspect_ratio is None:
        return None

    if isinstance(aspect_ratio, tuple) and len(aspect_ratio) == 2:
        w, h = aspect_ratio
        if not isinstance(w, int) or not isinstance(h, int):
            raise ValueError(f"aspect_ratio tuple values must be integers: {aspect_ratio!r}")
        if w <= 0 or h <= 0:
            raise ValueError(f"aspect_ratio tuple values must be positive: {aspect_ratio!r}")
        if w > MAX_IMAGE_DIMENSION or h > MAX_IMAGE_DIMENSION:
            raise ValueError(
                f"aspect_ratio values must be <= {MAX_IMAGE_DIMENSION}: {aspect_ratio!r}"
            )
        return (w, h)

    if isinstance(aspect_ratio, str):
        match = re.match(r"^\s*(\d+)\s*[:/]\s*(\d+)\s*$", aspect_ratio)
        if match:
            w, h = int(match.group(1)), int(match.group(2))
            if w <= 0 or h <= 0:
                raise ValueError(f"aspect_ratio values must be positive: {aspect_ratio!r}")
            if w > MAX_IMAGE_DIMENSION or h > MAX_IMAGE_DIMENSION:
                raise ValueError(
                    f"aspect_ratio values must be <= {MAX_IMAGE_DIMENSION}: {aspect_ratio!r}"
                )
            return (w, h)
        raise ValueError(f"Invalid aspect_ratio string: {aspect_ratio!r}")

    raise ValueError(f"Invalid aspect_ratio type: {type(aspect_ratio)}")


def parse_color(color: tuple[int, int, int] | str) -> tuple[int, int, int]:
    """Convert a color tuple or CSS hex string to an RGB tuple."""
    if isinstance(color, tuple) and len(color) == 3:
        if all(isinstance(c, int) and 0 <= c <= 255 for c in color):
            return color
        raise ValueError(f"RGB tuple values must be integers between 0 and 255: {color!r}")

    if isinstance(color, str):
        color = color.strip()
        if color.lower() == "white":
            return WHITE
        if color.lower() == "black":
            return (0, 0, 0)
        if color.startswith("#"):
            h = color.lstrip("#")
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            if len(h) != 6:
                raise ValueError(f"Invalid hex color length: {len(h)} (expected 3 or 6): {color!r}")
            try:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            except ValueError as exc:
                raise ValueError(f"Invalid hex color: {color!r}") from exc

    raise ValueError(f"Invalid color: {color!r}")


def _compute_target_size(
    img_width: int,
    img_height: int,
    max_width: int | None,
    max_height: int | None,
    aspect_ratio: tuple[int, int] | None,
) -> tuple[int, int]:
    """Compute the target output dimensions from bounds and aspect ratio."""
    if aspect_ratio is None:
        if max_width is None and max_height is None:
            return img_width, img_height
        if max_width is not None and max_height is not None:
            return max_width, max_height
        if max_width is not None:
            if img_width == 0:
                return max_width, 0
            return max_width, int(max_width * img_height / img_width)
        if max_height is not None:
            if img_height == 0:
                return 0, max_height
            return int(max_height * img_width / img_height), max_height
        return img_width, img_height

    aw, ah = aspect_ratio
    if aw <= 0 or ah <= 0:
        raise ValueError(f"aspect_ratio values must be positive: {aspect_ratio!r}")

    if max_width is not None and max_height is not None:
        w = max_width
        h = int(w * ah / aw)
        if h > max_height:
            h = max_height
            w = int(h * aw / ah)
        return w, h

    if max_width is not None:
        return max_width, int(max_width * ah / aw)

    if max_height is not None:
        return int(max_height * aw / ah), max_height

    # No bounds given; keep original width and adjust height to the aspect ratio.
    if img_width == 0:
        return 0, 0
    return img_width, int(img_width * ah / aw)


def _resolve_anchor(anchor: Anchor) -> tuple[float, float]:
    """Map an Anchor to (x_fraction, y_fraction) for offset calculation."""
    mapping: dict[Anchor, tuple[float, float]] = {
        Anchor.CENTER: (0.5, 0.5),
        Anchor.TOP: (0.5, 0.0),
        Anchor.BOTTOM: (0.5, 1.0),
        Anchor.LEFT: (0.0, 0.5),
        Anchor.RIGHT: (1.0, 0.5),
        Anchor.TOP_LEFT: (0.0, 0.0),
        Anchor.TOP_RIGHT: (1.0, 0.0),
        Anchor.BOTTOM_LEFT: (0.0, 1.0),
        Anchor.BOTTOM_RIGHT: (1.0, 1.0),
        Anchor.FACE: (0.5, 0.0),  # Fallback to top-center when no face detector.
    }
    return mapping[anchor]


def _anchor_offset(
    container_w: int,
    container_h: int,
    content_w: int,
    content_h: int,
    anchor: Anchor,
) -> tuple[int, int]:
    """Return the top-left offset to place a content box inside a container."""
    x_frac, y_frac = _resolve_anchor(anchor)
    max_x = container_w - content_w
    max_y = container_h - content_h
    return int(max_x * x_frac), int(max_y * y_frac)


def _fit_cover(
    img: Image.Image,
    target_w: int,
    target_h: int,
    anchor: Anchor,
) -> Image.Image:
    """Scale and crop the image to fill the target dimensions."""
    if img.width <= 0 or img.height <= 0:
        raise ValueError(f"Image has invalid dimensions: {img.width}x{img.height}")
    if img.width == target_w and img.height == target_h:
        return img

    img_aspect = img.width / img.height
    target_aspect = target_w / target_h

    if img_aspect > target_aspect:
        new_height = target_h
        new_width = max(target_w, int(new_height * img_aspect))
    else:
        new_width = target_w
        new_height = max(target_h, int(new_width / img_aspect))

    resized = img.resize((new_width, new_height), Resampling.LANCZOS)
    x, y = _anchor_offset(new_width, new_height, target_w, target_h, anchor)
    return resized.crop((x, y, x + target_w, y + target_h))


def _fit_contain(
    img: Image.Image,
    target_w: int,
    target_h: int,
    anchor: Anchor,
    background: tuple[int, int, int],
) -> Image.Image:
    """Scale the image to fit inside the target dimensions and pad with a background."""
    if img.width <= 0 or img.height <= 0:
        raise ValueError(f"Image has invalid dimensions: {img.width}x{img.height}")
    if img.width == target_w and img.height == target_h:
        return img

    img_aspect = img.width / img.height
    target_aspect = target_w / target_h

    if img_aspect > target_aspect:
        new_width = target_w
        new_height = max(1, int(new_width / img_aspect))
    else:
        new_height = target_h
        new_width = max(1, int(new_height * img_aspect))

    resized = img.resize((new_width, new_height), Resampling.LANCZOS)
    canvas = Image.new("RGB", (target_w, target_h), background)

    x, y = _anchor_offset(target_w, target_h, new_width, new_height, anchor)

    if resized.mode in ("RGBA", "LA"):
        canvas.paste(resized, (x, y), mask=resized.split()[-1])
    elif resized.mode == "P" and "transparency" in resized.info:
        rgba = resized.convert("RGBA")
        canvas.paste(rgba, (x, y), mask=rgba.split()[-1])
    else:
        canvas.paste(resized, (x, y))

    return canvas


def resize_image(
    img: Image.Image,
    *,
    max_width: int | None = None,
    max_height: int | None = None,
    keep_aspect_ratio: bool = True,
    fit: FitMode | str | None = None,
    anchor: Anchor | str = Anchor.CENTER,
    aspect_ratio: tuple[int, int] | str | None = None,
    background_color: tuple[int, int, int] | str = WHITE,
) -> Image.Image:
    """Resize an image respecting optional bounds and fit mode.

    Fit modes:
        - None or 'down': legacy thumbnail within max bounds, no upscaling.
        - 'cover': crop to fill the target dimensions.
        - 'contain': fit inside the target dimensions and pad.
        - 'fill': stretch to the target dimensions.

    The target dimensions are computed from max_width, max_height and the
    optional aspect_ratio. If a fit mode other than 'down' is used, the image
    may be upscaled to meet the target size.
    """
    if fit is None:
        if not max_width and not max_height:
            return img
        if keep_aspect_ratio:
            img.thumbnail(
                (max_width or img.width, max_height or img.height),
                Resampling.LANCZOS,
            )
            return img
        target_width = max_width or img.width
        target_height = max_height or img.height
        return img.resize((target_width, target_height), Resampling.LANCZOS)

    if isinstance(fit, str):
        fit = FitMode(fit)
    if isinstance(anchor, str):
        anchor = Anchor(anchor)

    parsed_aspect = parse_aspect_ratio(aspect_ratio)
    target_w, target_h = _compute_target_size(
        img.width,
        img.height,
        max_width,
        max_height,
        parsed_aspect,
    )

    # Avoid zero-sized targets.
    target_w = max(1, target_w)
    target_h = max(1, target_h)

    if fit == FitMode.DOWN:
        img.thumbnail((target_w, target_h), Resampling.LANCZOS)
        return img

    if fit == FitMode.FILL:
        return img.resize((target_w, target_h), Resampling.LANCZOS)

    if fit == FitMode.COVER:
        return _fit_cover(img, target_w, target_h, anchor)

    if fit == FitMode.CONTAIN:
        return _fit_contain(
            img,
            target_w,
            target_h,
            anchor,
            parse_color(background_color),
        )

    raise ValueError(f"Unknown fit mode: {fit}")


def build_save_kwargs(
    pillow_fmt: str,
    *,
    quality: int = 85,
    progressive: bool = True,
    optimize: bool = True,
    strip_metadata: bool = True,
    animated: bool = False,
    lossless: bool = False,
) -> dict[str, Any]:
    """Return Pillow-compatible save keyword arguments."""
    kwargs: dict[str, Any] = {"optimize": optimize}

    if pillow_fmt == "JPEG":
        kwargs["quality"] = quality
        kwargs["progressive"] = progressive
        if strip_metadata:
            kwargs["exif"] = b""
    elif pillow_fmt == "WEBP":
        kwargs["quality"] = quality
        kwargs["method"] = 6
        if lossless:
            kwargs["lossless"] = True
        if strip_metadata:
            kwargs["exif"] = b""
        if animated:
            kwargs["save_all"] = True
            kwargs["minimize"] = True
    elif pillow_fmt == "PNG":
        kwargs["compress_level"] = 9
    elif pillow_fmt == "GIF" and animated:
        kwargs["save_all"] = True
        kwargs["optimize"] = True

    return kwargs


def _pixel_data(img: Image.Image) -> list[Any]:
    """Return pixel data avoiding Pillow's deprecated getdata() when possible."""
    if hasattr(img, "get_flattened_data"):
        return list(img.get_flattened_data())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return list(cast(Iterable[Any], img.getdata()))


def strip_metadata_pillow(img: Image.Image, pillow_fmt: str) -> Image.Image:
    """Return a new image with all metadata removed (for non-JPEG/WEBP formats)."""
    if pillow_fmt in ("JPEG", "WEBP"):
        return img
    data = _pixel_data(img)
    clean = Image.new(img.mode, img.size)
    clean.putdata(data)
    if img.mode == "P":
        palette = img.getpalette()
        if palette is not None:
            clean.putpalette(palette)
        if "transparency" in img.info:
            clean.info["transparency"] = img.info["transparency"]
    return clean


def strip_exif_post_process(path: Path, pillow_fmt: str) -> None:
    """Use piexif to aggressively strip remaining EXIF after Pillow save."""
    if pillow_fmt not in ("JPEG", "WEBP"):
        return
    with contextlib.suppress(Exception):
        piexif.remove(str(path))


def resolve_and_adjust_path(
    img: Image.Image,
    output_path: Path,
    output_format: OutputFormat,
) -> tuple[Path, str]:
    """Resolve format and ensure output path has the correct extension.

    Returns:
        Tuple of (adjusted_output_path, pillow_format_name).

    """
    ext, pillow_fmt = resolve_output_format(img, output_path, output_format)
    if output_path.suffix.lower() != ext:
        output_path = output_path.with_suffix(ext)
    return output_path, pillow_fmt
