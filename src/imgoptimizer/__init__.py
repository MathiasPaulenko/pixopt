"""ImgOptimizer - A powerful image optimizer for web and storage."""

from imgoptimizer.models import OptimizationResult
from imgoptimizer.optimizer import (
    change_extension,
    convert_to_favicon,
    optimize_directory,
    optimize_image,
)

__version__ = "0.1.0"
__all__ = [
    "OptimizationResult",
    "change_extension",
    "convert_to_favicon",
    "optimize_directory",
    "optimize_image",
]
