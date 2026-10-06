"""pixopt - Fast Python image optimizer.

Resize, compress, convert, and generate responsive assets.
"""

from pixopt.adaptive_quality import find_quality_for_target_size
from pixopt.async_api import (
    async_batch_optimize,
    async_inspect_image,
    async_optimize_base64,
    async_optimize_bytes,
    async_optimize_image,
    async_scan_directory,
    async_scan_duplicates,
)
from pixopt.benchmark import BenchmarkResult, BenchmarkVariant, benchmark_formats
from pixopt.bundle import AssetBundle, BundleOptions, generate_asset_bundle
from pixopt.exceptions import (
    BundleError,
    ConversionError,
    EXIFError,
    ImageNotFoundError,
    InvalidParameterError,
    OptimizationError,
    PipelineError,
    PixoptError,
    ResizeError,
    UnsupportedFormatError,
    WatermarkError,
)
from pixopt.exif import EXIFGroup, apply_filtered_exif, filter_exif, get_exif_groups
from pixopt.html_comparison import generate_comparison_html
from pixopt.inspect import inspect_image
from pixopt.inventory import ScanEntry, ScanReport, scan_directory
from pixopt.io_bytes import (
    Base64Result,
    BytesResult,
    base64_to_image,
    bytes_to_image,
    image_to_base64,
    image_to_bytes,
    optimize_base64,
    optimize_bytes,
)
from pixopt.logging import StructuredFormatter, configure_logging, get_logger
from pixopt.models import Anchor, BatchReport, FitMode, ImageInfo, OptimizationResult, OutputFormat
from pixopt.nextgen import (
    ConversionResult,
    FormatSupport,
    FormatSupportInfo,
    NextGenFormat,
    convert_to_nextgen,
    detect_format_support,
    is_format_supported,
)
from pixopt.optimizer import (
    batch_optimize,
    change_extension,
    convert_to_favicon,
    optimize_directory,
    optimize_image,
    validate_optimize_params,
)
from pixopt.palette import ColorSwatch, PaletteResult, extract_palette
from pixopt.pdf_io import (
    PdfExportResult,
    PdfImportResult,
    PdfPageInfo,
    images_to_pdf,
    pdf_to_images,
)
from pixopt.perceptual import (
    DuplicateGroup,
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
from pixopt.pipeline import Pipeline, PipelineResult
from pixopt.placeholder import PlaceholderType, generate_placeholder
from pixopt.presets import (
    BUILTIN_PRESETS,
    apply_preset,
    get_preset_names,
    load_custom_presets,
    resolve_preset,
)
from pixopt.progress import ProgressCallback, ProgressInfo
from pixopt.quality import QualityMetrics, compare_images, compute_psnr, compute_ssim
from pixopt.smart_format import (
    count_unique_colors,
    detect_optimal_format,
    has_transparency,
    is_photo,
)
from pixopt.sprite import (
    SpriteLayout,
    SpriteResult,
    SpriteSlot,
    create_contact_sheet,
    create_sprite,
)
from pixopt.srcset_generator import SrcsetImage, generate_srcset_images
from pixopt.watermark import (
    WatermarkPosition,
    WatermarkResult,
    add_image_watermark,
    add_text_watermark,
)

__version__ = "1.3.0"
__all__ = [
    "__version__",
    "Anchor",
    "BUILTIN_PRESETS",
    "AssetBundle",
    "Base64Result",
    "BatchReport",
    "BenchmarkResult",
    "BenchmarkVariant",
    "BundleError",
    "BundleOptions",
    "BytesResult",
    "ColorSwatch",
    "ConversionError",
    "ConversionResult",
    "EXIFError",
    "EXIFGroup",
    "FitMode",
    "FormatSupport",
    "FormatSupportInfo",
    "HashResult",
    "ImageInfo",
    "ImageNotFoundError",
    "InvalidParameterError",
    "NextGenFormat",
    "OptimizationError",
    "OutputFormat",
    "PaletteResult",
    "PdfExportResult",
    "PdfImportResult",
    "PdfPageInfo",
    "PixoptError",
    "Pipeline",
    "PipelineError",
    "PipelineResult",
    "ProgressCallback",
    "ProgressInfo",
    "QualityMetrics",
    "PlaceholderType",
    "ResizeError",
    "ScanEntry",
    "ScanReport",
    "SpriteLayout",
    "SpriteResult",
    "SpriteSlot",
    "SrcsetImage",
    "OptimizationResult",
    "UnsupportedFormatError",
    "WatermarkError",
    "WatermarkPosition",
    "WatermarkResult",
    "ahash",
    "apply_preset",
    "apply_filtered_exif",
    "batch_optimize",
    "benchmark_formats",
    "change_extension",
    "compare_images",
    "compute_hash",
    "compute_psnr",
    "compute_ssim",
    "configure_logging",
    "convert_to_favicon",
    "convert_to_nextgen",
    "create_contact_sheet",
    "create_sprite",
    "dhash",
    "DuplicateGroup",
    "DuplicateReport",
    "count_unique_colors",
    "detect_optimal_format",
    "has_transparency",
    "is_photo",
    "detect_format_support",
    "extract_palette",
    "filter_exif",
    "find_duplicates",
    "find_quality_for_target_size",
    "get_exif_groups",
    "validate_optimize_params",
    "get_logger",
    "load_custom_presets",
    "add_image_watermark",
    "StructuredFormatter",
    "add_text_watermark",
    "async_batch_optimize",
    "async_inspect_image",
    "async_optimize_base64",
    "async_optimize_bytes",
    "async_optimize_image",
    "async_scan_directory",
    "async_scan_duplicates",
    "base64_to_image",
    "bytes_to_image",
    "generate_comparison_html",
    "generate_placeholder",
    "generate_srcset_images",
    "generate_asset_bundle",
    "get_preset_names",
    "hamming_distance",
    "image_to_base64",
    "image_to_bytes",
    "images_to_pdf",
    "inspect_image",
    "is_format_supported",
    "optimize_base64",
    "optimize_bytes",
    "optimize_directory",
    "optimize_image",
    "pdf_to_images",
    "phash",
    "resolve_preset",
    "scan_directory",
    "scan_duplicates",
]
