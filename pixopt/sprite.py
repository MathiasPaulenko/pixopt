"""Sprite / contact sheet generation.

Combine multiple images into a single sprite or contact sheet.
Useful for game dev and thumbnail indexes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from pixopt._units import MAX_IMAGE_DIMENSION, MAX_SPRITE_IMAGES, MAX_SPRITE_TOTAL_PIXELS, WHITE
from pixopt.image_ops import _open_image
from pixopt.logging import get_logger
from pixopt.utils import validate_no_parent_references

__all__ = [
    "SpriteLayout",
    "SpriteResult",
    "SpriteSlot",
    "create_sprite",
    "create_contact_sheet",
]

_logger = get_logger("sprite")

_BLACK: tuple[int, int, int] = (0, 0, 0)
_GRAY: tuple[int, int, int] = (200, 200, 200)


def _validate_sprite_params(
    cell_width: int | None,
    cell_height: int | None,
    columns: int | None,
    padding: int,
    label_height: int | None = None,
) -> None:
    """Validate sprite/contact sheet dimension parameters."""
    for name, value in (
        ("cell_width", cell_width),
        ("cell_height", cell_height),
    ):
        if value is not None and (value < 1 or value > MAX_IMAGE_DIMENSION):
            raise ValueError(f"{name} must be between 1 and {MAX_IMAGE_DIMENSION}, got {value}")

    if columns is not None and columns < 1:
        raise ValueError(f"columns must be positive, got {columns}")

    if padding < 0 or padding > MAX_IMAGE_DIMENSION:
        raise ValueError(f"padding must be between 0 and {MAX_IMAGE_DIMENSION}, got {padding}")

    if label_height is not None and (label_height < 0 or label_height > MAX_IMAGE_DIMENSION):
        raise ValueError(
            f"label_height must be between 0 and {MAX_IMAGE_DIMENSION}, got {label_height}"
        )


class SpriteLayout(str, Enum):
    """Layout strategy for arranging images in a sprite."""

    GRID = "grid"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


@dataclass
class SpriteSlot:
    """Information about a single image placed in a sprite."""

    index: int
    source: Path
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "source": str(self.source),
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class SpriteResult:
    """Result of creating a sprite or contact sheet."""

    output: Path
    layout: str
    columns: int
    rows: int
    cell_width: int
    cell_height: int
    total_images: int
    slots: list[SpriteSlot] = field(default_factory=list)
    width: int = 0
    height: int = 0
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": str(self.output),
            "layout": self.layout,
            "columns": self.columns,
            "rows": self.rows,
            "cell_width": self.cell_width,
            "cell_height": self.cell_height,
            "total_images": self.total_images,
            "slots": [s.to_dict() for s in self.slots],
            "width": self.width,
            "height": self.height,
            "success": self.success,
            "error": self.error,
        }


def create_sprite(
    images: Sequence[Path | str],
    output: Path | str,
    *,
    cell_width: int | None = None,
    cell_height: int | None = None,
    columns: int | None = None,
    layout: SpriteLayout | str = SpriteLayout.GRID,
    padding: int = 0,
    background: tuple[int, int, int] = WHITE,
    fmt: str = "PNG",
) -> SpriteResult:
    """Combine multiple images into a single sprite sheet.

    Each image is resized to fit within ``cell_width × cell_height``
    (keeping aspect ratio by default) and placed in a grid.

    Args:
        images: List of image file paths.
        output: Output sprite sheet path.
        cell_width: Width of each cell. If None, uses the max image width.
        cell_height: Height of each cell. If None, uses the max image height.
        columns: Number of columns (grid layout). If None, auto-calculated.
        layout: ``"grid"``, ``"horizontal"``, or ``"vertical"``.
        padding: Pixels between cells.
        background: Background color for empty areas.
        fmt: Output image format (PNG, JPEG, WEBP).

    Returns:
        A :class:`SpriteResult` with layout info and slot positions.

    Raises:
        ValueError: If the image list is empty.

    """
    _validate_sprite_params(cell_width, cell_height, columns, padding)

    output_path = Path(output)
    if error := validate_no_parent_references(output_path, "output"):
        raise ValueError(error)

    if not images:
        raise ValueError("images list cannot be empty")

    if len(images) > MAX_SPRITE_IMAGES:
        raise ValueError(f"Too many images for sprite (max {MAX_SPRITE_IMAGES}), got {len(images)}")

    for img_path in images:
        if error := validate_no_parent_references(Path(img_path), "source"):
            raise ValueError(error)

    if isinstance(layout, str):
        layout = SpriteLayout(layout)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    _logger.debug("Creating sprite", extra={"operation": "sprite", "path": str(output_path)})

    pil_images: list[Image.Image] = []
    try:
        total_source_pixels = 0
        for img_path in images:
            image: Image.Image
            with _open_image(Path(img_path), label="source") as opened:
                image = opened
            total_source_pixels += image.width * image.height
            if total_source_pixels > MAX_SPRITE_TOTAL_PIXELS:
                raise ValueError(
                    f"Sprite source pixel budget exceeded: {total_source_pixels} "
                    f"(max {MAX_SPRITE_TOTAL_PIXELS})"
                )
            pil_images.append(image)

        # Determine cell dimensions
        if cell_width is None:
            cell_width = max(img.width for img in pil_images)
        if cell_height is None:
            cell_height = max(img.height for img in pil_images)

        total = len(pil_images)

        # Determine layout
        if layout == SpriteLayout.HORIZONTAL:
            cols = total
            rows = 1
        elif layout == SpriteLayout.VERTICAL:
            cols = 1
            rows = total
        else:
            # Grid
            import math

            cols = columns if columns is not None else max(1, int(math.ceil(total**0.5)))
            rows = (total + cols - 1) // cols

        sheet_width = cols * cell_width + (cols - 1) * padding
        sheet_height = rows * cell_height + (rows - 1) * padding

        if sheet_width > MAX_IMAGE_DIMENSION or sheet_height > MAX_IMAGE_DIMENSION:
            raise ValueError(
                f"Sprite sheet dimensions too large: {sheet_width}x{sheet_height} "
                f"(max {MAX_IMAGE_DIMENSION})"
            )

        sheet = Image.new("RGB", (sheet_width, sheet_height), background)

        slots: list[SpriteSlot] = []
        for idx, img in enumerate(pil_images):
            row = idx // cols
            col = idx % cols
            x = col * (cell_width + padding)
            y = row * (cell_height + padding)

            # Resize image to fit within cell, preserving aspect ratio
            resized = _fit_image(img, cell_width, cell_height, background)

            # Center within cell
            offset_x = x + (cell_width - resized.width) // 2
            offset_y = y + (cell_height - resized.height) // 2

            sheet.paste(resized, (offset_x, offset_y))

            slots.append(
                SpriteSlot(
                    index=idx,
                    source=Path(images[idx]),
                    x=offset_x,
                    y=offset_y,
                    width=resized.width,
                    height=resized.height,
                )
            )

        pillow_fmt = fmt.upper()
        save_kwargs: dict[str, Any] = {}
        if pillow_fmt == "JPEG":
            save_kwargs["quality"] = 95
        sheet.save(output_path, pillow_fmt, **save_kwargs)

        result = SpriteResult(
            output=output_path,
            layout=layout.value,
            columns=cols,
            rows=rows,
            cell_width=cell_width,
            cell_height=cell_height,
            total_images=total,
            slots=slots,
            width=sheet_width,
            height=sheet_height,
            success=True,
        )

        _logger.info(
            "Sprite created",
            extra={"operation": "sprite", "path": str(output_path), "size_bytes": total},
        )

        return result

    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        _logger.error(
            "Sprite creation failed", extra={"operation": "sprite", "path": str(output_path)}
        )
        return SpriteResult(
            output=output_path,
            layout=layout.value if isinstance(layout, SpriteLayout) else str(layout),
            columns=0,
            rows=0,
            cell_width=cell_width or 0,
            cell_height=cell_height or 0,
            total_images=len(images),
            success=False,
            error=str(exc),
        )
    finally:
        for img in pil_images:
            img.close()


def create_contact_sheet(
    images: Sequence[Path | str],
    output: Path | str,
    *,
    cell_width: int = 200,
    cell_height: int = 200,
    columns: int | None = None,
    padding: int = 10,
    background: tuple[int, int, int] = WHITE,
    label_height: int = 20,
    fmt: str = "PNG",
) -> SpriteResult:
    """Create a contact sheet with labels showing image filenames.

    A contact sheet is a grid of thumbnails with text labels below each
    image, similar to a photo proof sheet.

    Args:
        images: List of image file paths.
        output: Output contact sheet path.
        cell_width: Width of each thumbnail cell.
        cell_height: Height of each thumbnail cell.
        columns: Number of columns. If None, auto-calculated.
        padding: Pixels between cells.
        background: Background color.
        label_height: Height of the label area below each image.
        fmt: Output image format.

    Returns:
        A :class:`SpriteResult` with layout info and slot positions.

    Raises:
        ValueError: If the image list is empty.

    """
    _validate_sprite_params(cell_width, cell_height, columns, padding, label_height)

    output_path = Path(output)
    if error := validate_no_parent_references(output_path, "output"):
        raise ValueError(error)

    if not images:
        raise ValueError("images list cannot be empty")

    if len(images) > MAX_SPRITE_IMAGES:
        raise ValueError(
            f"Too many images for contact sheet (max {MAX_SPRITE_IMAGES}), got {len(images)}"
        )

    for img_path in images:
        if error := validate_no_parent_references(Path(img_path), "source"):
            raise ValueError(error)

    import math

    output_path.parent.mkdir(parents=True, exist_ok=True)

    _logger.debug(
        "Creating contact sheet", extra={"operation": "contact_sheet", "path": str(output_path)}
    )

    pil_images: list[Image.Image] = []
    try:
        total_source_pixels = 0
        for img_path in images:
            image: Image.Image
            with _open_image(Path(img_path), label="source") as opened:
                image = opened
            total_source_pixels += image.width * image.height
            if total_source_pixels > MAX_SPRITE_TOTAL_PIXELS:
                raise ValueError(
                    f"Contact sheet source pixel budget exceeded: {total_source_pixels} "
                    f"(max {MAX_SPRITE_TOTAL_PIXELS})"
                )
            pil_images.append(image)

        total = len(pil_images)
        cols = columns if columns is not None else max(1, int(math.ceil(total**0.5)))
        rows = (total + cols - 1) // cols

        full_cell_height = cell_height + label_height
        sheet_width = cols * cell_width + (cols + 1) * padding
        sheet_height = rows * full_cell_height + (rows + 1) * padding

        if sheet_width > MAX_IMAGE_DIMENSION or sheet_height > MAX_IMAGE_DIMENSION:
            raise ValueError(
                f"Contact sheet dimensions too large: {sheet_width}x{sheet_height} "
                f"(max {MAX_IMAGE_DIMENSION})"
            )

        sheet = Image.new("RGB", (sheet_width, sheet_height), background)
        draw = ImageDraw.Draw(sheet)

        slots: list[SpriteSlot] = []
        for idx, img in enumerate(pil_images):
            row = idx // cols
            col = idx % cols
            x = padding + col * (cell_width + padding)
            y = padding + row * (full_cell_height + padding)

            resized = _fit_image(img, cell_width, cell_height, background)
            offset_x = x + (cell_width - resized.width) // 2
            offset_y = y + (cell_height - resized.height) // 2

            sheet.paste(resized, (offset_x, offset_y))

            # Draw label
            label = Path(images[idx]).name
            label_y = y + cell_height + 2
            draw.text((x + 2, label_y), label, fill=_BLACK)

            # Draw border
            draw.rectangle(
                [x - 1, y - 1, x + cell_width, y + cell_height],
                outline=_GRAY,
            )

            slots.append(
                SpriteSlot(
                    index=idx,
                    source=Path(images[idx]),
                    x=offset_x,
                    y=offset_y,
                    width=resized.width,
                    height=resized.height,
                )
            )

        pillow_fmt = fmt.upper()
        save_kwargs: dict[str, Any] = {}
        if pillow_fmt == "JPEG":
            save_kwargs["quality"] = 95
        sheet.save(output_path, pillow_fmt, **save_kwargs)

        result = SpriteResult(
            output=output_path,
            layout="contact_sheet",
            columns=cols,
            rows=rows,
            cell_width=cell_width,
            cell_height=cell_height,
            total_images=total,
            slots=slots,
            width=sheet_width,
            height=sheet_height,
            success=True,
        )

        _logger.info(
            "Contact sheet created",
            extra={"operation": "contact_sheet", "path": str(output_path), "size_bytes": total},
        )

        return result

    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        _logger.error(
            "Contact sheet failed", extra={"operation": "contact_sheet", "path": str(output_path)}
        )
        return SpriteResult(
            output=output_path,
            layout="contact_sheet",
            columns=0,
            rows=0,
            cell_width=cell_width,
            cell_height=cell_height,
            total_images=len(images),
            success=False,
            error=str(exc),
        )
    finally:
        for img in pil_images:
            img.close()


def _fit_image(
    img: Image.Image,
    target_w: int,
    target_h: int,
    background: tuple[int, int, int] = WHITE,
) -> Image.Image:
    """Resize image to fit within target dimensions, preserving aspect ratio."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", img.size, background)
        bg.paste(rgba, mask=rgba.split()[3])
        rgba.close()
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if img.width <= 0 or img.height <= 0:
        raise ValueError(f"Image has invalid dimensions: {img.width}x{img.height}")

    ratio = min(target_w / img.width, target_h / img.height)
    new_w = max(1, int(img.width * ratio))
    new_h = max(1, int(img.height * ratio))
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
