"""Map file extensions / user choices to Pillow format names."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from pixopt.constants import EXT_TO_FORMAT, FORMAT_MAP, FORMAT_TO_EXT
from pixopt.models import OutputFormat

__all__ = ["resolve_output_format"]


def resolve_output_format(
    img: Image.Image,
    output_path: Path,
    fmt: OutputFormat,
) -> tuple[str, str]:
    """Resolve the actual file extension and Pillow format name.

    Returns:
        Tuple of (extension, pillow_format_name).

    """
    if fmt == OutputFormat.ORIGINAL:
        filename = getattr(img, "filename", None) or ""
        original_ext = Path(filename).suffix.lower()
        pillow_fmt = EXT_TO_FORMAT.get(original_ext, img.format or "JPEG")
        if pillow_fmt not in FORMAT_TO_EXT:
            pillow_fmt = "JPEG"
        return original_ext or ".jpg", pillow_fmt

    if fmt == OutputFormat.AUTO:
        ext = output_path.suffix.lower()
        pillow_fmt = EXT_TO_FORMAT.get(ext, "JPEG")
        # If the path has no suffix or an unknown one, use the canonical
        # extension for the resolved format so the saved file is identifiable.
        if ext not in EXT_TO_FORMAT:
            ext = FORMAT_TO_EXT[pillow_fmt]
        return ext, pillow_fmt

    pillow_fmt = FORMAT_MAP[fmt]
    ext = FORMAT_TO_EXT[pillow_fmt]
    return ext, pillow_fmt
