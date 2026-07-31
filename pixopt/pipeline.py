"""Pipeline builder for chaining image operations.

Chain operations (open, resize, convert, watermark, optimize) in a single
``Pipeline`` object.  Useful for complex workflows and MCP tool composition.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from PIL import Image

from pixopt._units import WHITE
from pixopt.constants import FORMAT_MAP, FORMAT_TO_EXT
from pixopt.image_ops import (
    _open_image,
    apply_exif_orientation,
    build_save_kwargs,
    convert_mode,
    resize_image,
    strip_exif_post_process,
    strip_metadata_pillow,
)
from pixopt.logging import get_logger
from pixopt.models import Anchor, FitMode, OutputFormat
from pixopt.utils import validate_no_parent_references
from pixopt.watermark import WatermarkPosition, add_image_watermark, add_text_watermark

__all__ = ["PipelineResult", "Pipeline"]


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""

    output_path: Path
    width: int
    height: int
    format: str
    size_bytes: int
    steps_executed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_path": str(self.output_path),
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "steps_executed": list(self.steps_executed),
        }


class _OpKind(str, Enum):
    OPEN = "open"
    AUTO_ORIENT = "auto_orient"
    RESIZE = "resize"
    CONVERT = "convert"
    WATERMARK_TEXT = "watermark_text"
    WATERMARK_IMAGE = "watermark_image"
    OPTIMIZE = "optimize"


@dataclass
class _Op:
    kind: _OpKind
    params: dict[str, Any] = field(default_factory=dict)


class Pipeline:
    """Chainable image processing pipeline.

    Build a sequence of operations and execute them in one call::

        pipeline = (
            Pipeline()
            .open("photo.jpg")
            .resize(max_width=800)
            .watermark_text("© 2025", position="bottom-right")
            .optimize(quality=85, output_format="webp")
            .save("output/photo.webp")
        )
        result = pipeline.run()

    Each method returns ``self`` for fluent chaining.
    """

    def __init__(self) -> None:
        self._ops: list[_Op] = []
        self._source: Path | None = None

    # -- Operation builders ------------------------------------------------

    def open(self, source: Path | str) -> Pipeline:
        """Set the source image to process."""
        src = Path(source)
        if error := validate_no_parent_references(src, "source"):
            raise ValueError(error)
        self._source = src
        self._ops.append(_Op(_OpKind.OPEN, {"source": self._source}))
        return self

    def auto_orient(self) -> Pipeline:
        """Apply EXIF orientation tag."""
        self._ops.append(_Op(_OpKind.AUTO_ORIENT))
        return self

    def resize(
        self,
        *,
        max_width: int | None = None,
        max_height: int | None = None,
        fit: FitMode | str | None = None,
        anchor: Anchor | str = Anchor.CENTER,
        aspect_ratio: tuple[int, int] | str | None = None,
        background_color: tuple[int, int, int] | str | None = None,
    ) -> Pipeline:
        """Resize the image with optional fit mode."""
        self._ops.append(
            _Op(
                _OpKind.RESIZE,
                {
                    "max_width": max_width,
                    "max_height": max_height,
                    "fit": fit,
                    "anchor": anchor,
                    "aspect_ratio": aspect_ratio,
                    "background_color": background_color,
                },
            )
        )
        return self

    def convert(self, mode: str = "RGB") -> Pipeline:
        """Convert the image color mode (e.g. ``"RGB"``, ``"RGBA"``, ``"L"``)."""
        self._ops.append(_Op(_OpKind.CONVERT, {"mode": mode}))
        return self

    def watermark_text(
        self,
        text: str,
        *,
        position: WatermarkPosition | str = WatermarkPosition.BOTTOM_RIGHT,
        opacity: float = 0.5,
        padding: int = 20,
        font_size: int = 48,
        font_path: Path | str | None = None,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> Pipeline:
        """Add a text watermark overlay."""
        if isinstance(position, str):
            position = WatermarkPosition(position)
        if font_path is not None and (
            error := validate_no_parent_references(Path(font_path), "font_path")
        ):
            raise ValueError(error)
        self._ops.append(
            _Op(
                _OpKind.WATERMARK_TEXT,
                {
                    "text": text,
                    "position": position,
                    "opacity": opacity,
                    "padding": padding,
                    "font_size": font_size,
                    "font_path": font_path,
                    "color": color,
                },
            )
        )
        return self

    def watermark_image(
        self,
        watermark_path: Path | str,
        *,
        position: WatermarkPosition | str = WatermarkPosition.BOTTOM_RIGHT,
        opacity: float = 0.5,
        padding: int = 20,
        scale: float = 0.3,
    ) -> Pipeline:
        """Add an image watermark overlay."""
        if isinstance(position, str):
            position = WatermarkPosition(position)
        if error := validate_no_parent_references(Path(watermark_path), "watermark_path"):
            raise ValueError(error)
        self._ops.append(
            _Op(
                _OpKind.WATERMARK_IMAGE,
                {
                    "watermark_path": Path(watermark_path),
                    "position": position,
                    "opacity": opacity,
                    "padding": padding,
                    "scale": scale,
                },
            )
        )
        return self

    def optimize(
        self,
        *,
        quality: int = 85,
        output_format: OutputFormat | str = OutputFormat.WEBP,
        progressive: bool = True,
        optimize: bool = True,
        lossless: bool = False,
        strip_metadata: bool = True,
    ) -> Pipeline:
        """Configure optimization parameters for the final save."""
        if isinstance(output_format, str):
            try:
                output_format = OutputFormat(output_format)
            except ValueError as exc:
                raise ValueError(f"Invalid output_format: {output_format}") from exc
        self._ops.append(
            _Op(
                _OpKind.OPTIMIZE,
                {
                    "quality": quality,
                    "output_format": output_format,
                    "progressive": progressive,
                    "optimize": optimize,
                    "lossless": lossless,
                    "strip_metadata": strip_metadata,
                },
            )
        )
        return self

    def save(self, output: Path | str) -> Pipeline:
        """Set the output path for the final image."""
        out = Path(output)
        if error := validate_no_parent_references(out, "output"):
            raise ValueError(error)
        self._ops.append(_Op(_OpKind.OPEN, {"output": out}))  # placeholder
        self._output = out
        return self

    # -- Execution ---------------------------------------------------------

    def run(self) -> PipelineResult:
        """Execute all queued operations and return a :class:`PipelineResult`.

        Raises:
            ValueError: If no source image was set.
            FileNotFoundError: If the source image does not exist.

        """
        if self._source is None:
            raise ValueError("No source image set. Call .open(path) first.")

        logger = get_logger("pipeline")
        logger.debug("Pipeline started", extra={"operation": "pipeline", "path": str(self._source)})

        output = Path(getattr(self, "_output", None) or self._source.with_suffix(".webp"))
        if error := validate_no_parent_references(output, "output"):
            raise ValueError(error)

        steps: list[str] = []
        img: Image.Image | None = None
        opt_params: dict[str, Any] = {
            "quality": 85,
            "output_format": OutputFormat.WEBP,
            "progressive": True,
            "optimize": True,
            "lossless": False,
            "strip_metadata": True,
        }

        for op in self._ops:
            if op.kind == _OpKind.OPEN:
                if "source" in op.params:
                    with _open_image(op.params["source"], label="source") as opened:
                        opened.load()
                        img = opened
                    steps.append(f"open({op.params['source'].name})")
                elif "output" in op.params:
                    pass  # output path already captured

            elif op.kind == _OpKind.AUTO_ORIENT and img is not None:
                img = apply_exif_orientation(img)
                steps.append("auto_orient")

            elif op.kind == _OpKind.RESIZE and img is not None:
                fit_val = op.params.get("fit")
                if isinstance(fit_val, str):
                    try:
                        fit_val = FitMode(fit_val)
                    except ValueError as exc:
                        raise ValueError(f"Invalid fit value: {fit_val}") from exc
                anchor_val = op.params.get("anchor", Anchor.CENTER)
                if isinstance(anchor_val, str):
                    try:
                        anchor_val = Anchor(anchor_val)
                    except ValueError as exc:
                        raise ValueError(f"Invalid anchor value: {anchor_val}") from exc
                img = resize_image(
                    img,
                    max_width=op.params.get("max_width"),
                    max_height=op.params.get("max_height"),
                    fit=fit_val,
                    anchor=anchor_val,
                    aspect_ratio=op.params.get("aspect_ratio"),
                    background_color=op.params.get("background_color", WHITE),
                )
                steps.append(f"resize({img.width}x{img.height})")

            elif op.kind == _OpKind.CONVERT and img is not None:
                img = img.convert(op.params["mode"])
                steps.append(f"convert({op.params['mode']})")

            elif op.kind == _OpKind.WATERMARK_TEXT and img is not None:
                fd, tmp_name = tempfile.mkstemp(
                    prefix="pixopt_wm_", suffix=".png", dir=tempfile.gettempdir()
                )
                os.close(fd)
                tmp_path = Path(tmp_name)
                try:
                    img.save(tmp_path, "PNG")
                    wm_result = add_text_watermark(
                        tmp_path,
                        tmp_path,
                        op.params["text"],
                        position=op.params["position"],
                        opacity=op.params["opacity"],
                        padding=op.params["padding"],
                        font_size=op.params["font_size"],
                        font_path=op.params["font_path"],
                        color=op.params["color"],
                    )
                    with _open_image(wm_result.output_path, label="watermark result") as opened:
                        opened.load()
                        img.close()
                        img = opened
                finally:
                    tmp_path.unlink(missing_ok=True)
                steps.append(f"watermark_text({op.params['text']!r})")

            elif op.kind == _OpKind.WATERMARK_IMAGE and img is not None:
                fd, tmp_name = tempfile.mkstemp(
                    prefix="pixopt_wm_", suffix=".png", dir=tempfile.gettempdir()
                )
                os.close(fd)
                tmp_path = Path(tmp_name)
                try:
                    img.save(tmp_path, "PNG")
                    wm_result = add_image_watermark(
                        tmp_path,
                        tmp_path,
                        op.params["watermark_path"],
                        position=op.params["position"],
                        opacity=op.params["opacity"],
                        padding=op.params["padding"],
                        scale=op.params["scale"],
                    )
                    with _open_image(wm_result.output_path, label="watermark result") as opened:
                        opened.load()
                        img = opened
                finally:
                    tmp_path.unlink(missing_ok=True)
                steps.append("watermark_image")

            elif op.kind == _OpKind.OPTIMIZE:
                opt_params.update(op.params)
                steps.append(f"optimize(quality={op.params['quality']})")

        if img is None:
            raise ValueError("Pipeline produced no image. Did you call .open()?")

        output.parent.mkdir(parents=True, exist_ok=True)

        out_fmt: OutputFormat = opt_params["output_format"]
        pillow_fmt = FORMAT_MAP.get(out_fmt, "WEBP")
        ext = FORMAT_TO_EXT.get(pillow_fmt, ".webp")

        if output.suffix == "":
            output = output.with_suffix(ext)

        try:
            img = convert_mode(img, pillow_fmt)
            save_kwargs = build_save_kwargs(
                pillow_fmt,
                quality=opt_params["quality"],
                progressive=opt_params["progressive"],
                optimize=opt_params["optimize"],
                lossless=opt_params["lossless"],
                strip_metadata=opt_params["strip_metadata"],
            )

            if opt_params["strip_metadata"]:
                img = strip_metadata_pillow(img, pillow_fmt)

            img.save(output, format=pillow_fmt, **save_kwargs)

            if opt_params["strip_metadata"]:
                strip_exif_post_process(output, pillow_fmt)

            size_bytes = output.stat().st_size

            return PipelineResult(
                output_path=output,
                width=img.width,
                height=img.height,
                format=pillow_fmt,
                size_bytes=size_bytes,
                steps_executed=steps,
            )
        finally:
            img.close()

    # -- Introspection -----------------------------------------------------

    @property
    def steps(self) -> list[str]:
        """Return a human-readable list of queued operation names."""
        labels: list[str] = []
        for op in self._ops:
            if op.kind == _OpKind.OPEN and "source" in op.params:
                labels.append(f"open({op.params['source']})")
            elif op.kind == _OpKind.AUTO_ORIENT:
                labels.append("auto_orient")
            elif op.kind == _OpKind.RESIZE:
                labels.append(f"resize({op.params})")
            elif op.kind == _OpKind.CONVERT:
                labels.append(f"convert({op.params['mode']})")
            elif op.kind == _OpKind.WATERMARK_TEXT:
                labels.append(f"watermark_text({op.params['text']!r})")
            elif op.kind == _OpKind.WATERMARK_IMAGE:
                labels.append("watermark_image")
            elif op.kind == _OpKind.OPTIMIZE:
                labels.append(f"optimize(quality={op.params['quality']})")
        return labels
