"""pixopt - Fast Python image optimizer. Resize, compress, convert,
and generate responsive assets."""

from pixopt.models import OptimizationResult
from pixopt.optimizer import (
    change_extension,
    convert_to_favicon,
    optimize_directory,
    optimize_image,
)

__version__ = "1.0.0"
__all__ = [
    "OptimizationResult",
    "change_extension",
    "convert_to_favicon",
    "optimize_directory",
    "optimize_image",
]
