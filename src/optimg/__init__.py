"""optimg - Fast Python image optimizer. Resize, compress, convert, and generate responsive assets."""

from optimg.models import OptimizationResult
from optimg.optimizer import (
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
