"""pixopt - Fast Python image optimizer.

Resize, compress, convert, and generate responsive assets.
"""

from pixopt.html_comparison import generate_comparison_html
from pixopt.models import OptimizationResult, OutputFormat
from pixopt.optimizer import (
    change_extension,
    convert_to_favicon,
    optimize_directory,
    optimize_image,
)
from pixopt.placeholder import PlaceholderType, generate_placeholder
from pixopt.smart_format import detect_optimal_format
from pixopt.srcset_generator import SrcsetImage, generate_srcset_images

__version__ = "1.1.1"
__all__ = [
    "OutputFormat",
    "PlaceholderType",
    "SrcsetImage",
    "OptimizationResult",
    "change_extension",
    "convert_to_favicon",
    "detect_optimal_format",
    "generate_comparison_html",
    "generate_placeholder",
    "generate_srcset_images",
    "optimize_directory",
    "optimize_image",
]
