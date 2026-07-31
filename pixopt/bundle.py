"""Asset bundle generation.

From one source image, generate hero, thumbnail, og:image, favicon,
srcset, LQIP, blurhash and palette in a single call.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pixopt._units import (
    MAX_BUNDLE_PALETTE_N,
    MAX_FAVICON_SIZES,
    MAX_IMAGE_DIMENSION,
    MAX_QUALITY,
    MAX_SRCSET_WIDTHS,
    MIN_QUALITY,
)
from pixopt.exceptions import ImageNotFoundError
from pixopt.image_ops import _open_image
from pixopt.logging import get_logger
from pixopt.models import OptimizationResult, OutputFormat
from pixopt.optimizer import convert_to_favicon, optimize_image
from pixopt.palette import PaletteResult, extract_palette
from pixopt.placeholder import (
    extract_dominant_color,
    generate_blurhash,
    generate_lqip_datauri,
)
from pixopt.srcset_generator import SrcsetImage, generate_srcset_images
from pixopt.utils import validate_no_parent_references

__all__ = ["AssetBundle", "BundleOptions", "generate_asset_bundle"]

_DEFAULT_SRCSET_WIDTHS = [320, 640, 960, 1280, 1920]
_DEFAULT_FAVICON_SIZES = [16, 32, 48, 64, 128, 256]
_DEFAULT_HERO_WIDTH = 1920
_DEFAULT_THUMBNAIL_WIDTH = 300
_DEFAULT_OG_WIDTH = 1200
_DEFAULT_OG_HEIGHT = 630
_DEFAULT_PALETTE_N = 6


@dataclass
class BundleOptions:
    """Configuration for asset bundle generation."""

    hero_width: int = _DEFAULT_HERO_WIDTH
    thumbnail_width: int = _DEFAULT_THUMBNAIL_WIDTH
    og_width: int = _DEFAULT_OG_WIDTH
    og_height: int = _DEFAULT_OG_HEIGHT
    favicon_sizes: list[int] = field(default_factory=lambda: list(_DEFAULT_FAVICON_SIZES))
    srcset_widths: list[int] = field(default_factory=lambda: list(_DEFAULT_SRCSET_WIDTHS))
    palette_n: int = _DEFAULT_PALETTE_N
    quality: int = 85
    lqip_size: int = 32
    lqip_quality: int = 20
    generate_hero: bool = True
    generate_thumbnail: bool = True
    generate_og: bool = True
    generate_favicon: bool = True
    generate_srcset: bool = True
    generate_lqip: bool = True
    generate_blurhash: bool = True
    generate_palette: bool = True
    generate_dominant_color: bool = True

    def __post_init__(self) -> None:
        """Validate bundle options after construction."""
        for name in ("hero_width", "thumbnail_width", "og_width", "og_height"):
            value = getattr(self, name)
            if value < 1 or value > MAX_IMAGE_DIMENSION:
                raise ValueError(f"{name} must be between 1 and {MAX_IMAGE_DIMENSION}, got {value}")

        if not MIN_QUALITY <= self.quality <= MAX_QUALITY:
            raise ValueError(
                f"quality must be between {MIN_QUALITY} and {MAX_QUALITY}, got {self.quality}"
            )

        if self.lqip_size < 1 or self.lqip_size > MAX_IMAGE_DIMENSION:
            raise ValueError(
                f"lqip_size must be between 1 and {MAX_IMAGE_DIMENSION}, got {self.lqip_size}"
            )

        if not MIN_QUALITY <= self.lqip_quality <= MAX_QUALITY:
            raise ValueError(
                f"lqip_quality must be between {MIN_QUALITY} and {MAX_QUALITY}, "
                f"got {self.lqip_quality}"
            )

        if not 1 <= self.palette_n <= MAX_BUNDLE_PALETTE_N:
            raise ValueError(
                f"palette_n must be between 1 and {MAX_BUNDLE_PALETTE_N}, got {self.palette_n}"
            )

        if len(self.srcset_widths) > MAX_SRCSET_WIDTHS:
            raise ValueError(
                f"srcset_widths must not exceed {MAX_SRCSET_WIDTHS} entries, "
                f"got {len(self.srcset_widths)}"
            )

        for size in self.srcset_widths:
            if size < 1 or size > MAX_IMAGE_DIMENSION:
                raise ValueError(
                    f"srcset width must be between 1 and {MAX_IMAGE_DIMENSION}, got {size}"
                )

        if len(self.favicon_sizes) > MAX_FAVICON_SIZES:
            raise ValueError(
                f"favicon_sizes must not exceed {MAX_FAVICON_SIZES} entries, "
                f"got {len(self.favicon_sizes)}"
            )

        for size in self.favicon_sizes:
            if size < 1 or size > MAX_IMAGE_DIMENSION:
                raise ValueError(
                    f"favicon size must be between 1 and {MAX_IMAGE_DIMENSION}, got {size}"
                )


@dataclass
class AssetBundle:
    """Result of asset bundle generation from a single source image."""

    source_path: Path
    output_dir: Path
    hero: OptimizationResult | None = None
    thumbnail: OptimizationResult | None = None
    og_image: OptimizationResult | None = None
    favicon: OptimizationResult | None = None
    srcset_images: list[SrcsetImage] = field(default_factory=list)
    lqip_data_uri: str | None = None
    blurhash: str | None = None
    dominant_color: str | None = None
    palette: PaletteResult | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""

        def _opt_dict(r: OptimizationResult | None) -> dict[str, Any] | None:
            if r is None:
                return None
            d = asdict(r)
            d["source_path"] = str(d["source_path"])
            d["output_path"] = str(d["output_path"])
            return d

        return {
            "source_path": str(self.source_path),
            "output_dir": str(self.output_dir),
            "hero": _opt_dict(self.hero),
            "thumbnail": _opt_dict(self.thumbnail),
            "og_image": _opt_dict(self.og_image),
            "favicon": _opt_dict(self.favicon),
            "srcset_images": [
                {"width": s.width, "output_path": str(s.output_path), "size_bytes": s.size_bytes}
                for s in self.srcset_images
            ],
            "lqip_data_uri": self.lqip_data_uri,
            "blurhash": self.blurhash,
            "dominant_color": self.dominant_color,
            "palette": self.palette.to_dict() if self.palette else None,
        }


def generate_asset_bundle(
    source: Path | str,
    output_dir: Path | str,
    *,
    options: BundleOptions | None = None,
) -> AssetBundle:
    """Generate a complete asset bundle from a single source image.

    Produces hero image, thumbnail, og:image, favicon, srcset variants,
    LQIP data URI, blurhash, dominant color, and color palette.

    Args:
        source: Path to the source image.
        output_dir: Directory where all generated assets are written.
        options: Configuration for what to generate and sizing parameters.

    Returns:
        An :class:`AssetBundle` with all generated assets.

    Raises:
        FileNotFoundError: If the source image does not exist.

    """
    source_path = Path(source)
    if not source_path.exists():
        raise ImageNotFoundError(source_path)

    opts = options or BundleOptions()
    out_dir = Path(output_dir)
    if error := validate_no_parent_references(out_dir, "output_dir"):
        raise ValueError(error)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger = get_logger("bundle")
    logger.info(
        "Asset bundle generation started", extra={"operation": "bundle", "path": str(source_path)}
    )

    stem = source_path.stem
    bundle = AssetBundle(source_path=source_path, output_dir=out_dir)

    # Hero image
    if opts.generate_hero:
        hero_path = out_dir / f"{stem}-hero.webp"
        bundle.hero = optimize_image(
            source_path,
            hero_path,
            max_width=opts.hero_width,
            quality=opts.quality,
            output_format=OutputFormat.WEBP,
        )

    # Thumbnail
    if opts.generate_thumbnail:
        thumb_path = out_dir / f"{stem}-thumb.webp"
        bundle.thumbnail = optimize_image(
            source_path,
            thumb_path,
            max_width=opts.thumbnail_width,
            quality=opts.quality,
            output_format=OutputFormat.WEBP,
        )

    # og:image (1200x630, cover crop)
    if opts.generate_og:
        og_path = out_dir / f"{stem}-og.jpg"
        bundle.og_image = optimize_image(
            source_path,
            og_path,
            max_width=opts.og_width,
            max_height=opts.og_height,
            fit="cover",
            quality=opts.quality,
            output_format=OutputFormat.JPEG,
        )

    # Favicon
    if opts.generate_favicon:
        fav_path = out_dir / f"{stem}.ico"
        bundle.favicon = convert_to_favicon(
            source_path,
            fav_path,
            sizes=opts.favicon_sizes,
        )

    # Srcset variants
    if opts.generate_srcset:
        srcset_dir = out_dir / "srcset"
        bundle.srcset_images = generate_srcset_images(
            source_path,
            srcset_dir,
            opts.srcset_widths,
            quality=opts.quality,
            output_format="WEBP",
        )

    # LQIP, blurhash, dominant color — all from the loaded image
    if opts.generate_lqip or opts.generate_blurhash or opts.generate_dominant_color:
        with _open_image(source_path, label="source") as img:
            img.load()
            if opts.generate_lqip:
                bundle.lqip_data_uri = generate_lqip_datauri(
                    img,
                    size=opts.lqip_size,
                    quality=opts.lqip_quality,
                )
            if opts.generate_blurhash:
                bundle.blurhash = generate_blurhash(img)
            if opts.generate_dominant_color:
                bundle.dominant_color = extract_dominant_color(img)

    # Color palette
    if opts.generate_palette:
        bundle.palette = extract_palette(source_path, n=opts.palette_n)

    return bundle
