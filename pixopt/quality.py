"""Image quality metrics: SSIM and PSNR.

Provides functions to compare an original image against an optimized/modified
version using Structural Similarity Index (SSIM) and Peak Signal-to-Noise
Ratio (PSNR).  Useful for CI gates and automated quality selection.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from pixopt._units import MAX_SSIM_PIXELS
from pixopt.image_ops import _open_image

__all__ = ["QualityMetrics", "compute_psnr", "compute_ssim", "compare_images"]


@dataclass(frozen=True)
class QualityMetrics:
    """Quality comparison metrics between two images."""

    ssim: float
    psnr: float | None  # None if images are identical (PSNR = infinity)
    mse: float
    original_path: Path
    compared_path: Path
    width: int
    height: int

    @property
    def verdict(self) -> str:
        """Human-readable quality verdict."""
        if self.ssim >= 0.95:
            return "excellent"
        if self.ssim >= 0.85:
            return "good"
        if self.ssim >= 0.70:
            return "fair"
        return "poor"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation."""
        d = asdict(self)
        d["original_path"] = str(d["original_path"])
        d["compared_path"] = str(d["compared_path"])
        d["psnr"] = self.psnr if self.psnr is not None else None
        d["verdict"] = self.verdict
        return d


def _load_as_array(path: Path | str) -> npt.NDArray[np.float32]:
    """Load an image as a float32 numpy array in RGB mode."""
    with _open_image(path, label="source") as img:
        rgb = img.convert("RGB")
        try:
            return np.asarray(rgb, dtype=np.float32)
        finally:
            rgb.close()


def compute_mse(img1: npt.NDArray[Any], img2: npt.NDArray[Any]) -> float:
    """Compute Mean Squared Error between two image arrays."""
    return float(np.mean((img1 - img2) ** 2))


def compute_psnr(mse: float, max_pixel: float = 255.0) -> float | None:
    """Compute PSNR from MSE.

    Returns None if MSE is 0 (images are identical, PSNR = infinity).
    """
    if mse == 0:
        return None
    return 10.0 * math.log10((max_pixel**2) / mse)


def compute_ssim(
    img1: npt.NDArray[Any],
    img2: npt.NDArray[Any],
    *,
    win_size: int = 7,
    data_range: float = 255.0,
) -> float:
    """Compute the Structural Similarity Index (SSIM) between two images.

    Uses a sliding window approach with a Gaussian-free uniform window.
    Works on grayscale (2D) or multi-channel (3D) arrays.

    Args:
        img1: First image as a numpy array.
        img2: Second image as a numpy array (same shape as img1).
        win_size: Side length of the sliding window (must be odd).
        data_range: Maximum pixel value (255 for 8-bit images).

    Returns:
        SSIM value in [-1, 1], where 1 means identical structure.
    """
    if img1.shape != img2.shape:
        msg = f"Image shapes don't match: {img1.shape} vs {img2.shape}"
        raise ValueError(msg)

    if win_size < 3 or win_size % 2 == 0:
        raise ValueError(f"win_size must be an odd integer >= 3, got {win_size}")
    if data_range <= 0:
        raise ValueError(f"data_range must be positive, got {data_range}")

    if img1.shape[0] * img1.shape[1] > MAX_SSIM_PIXELS:
        raise ValueError(
            f"SSIM pixel budget exceeded: {img1.shape[0] * img1.shape[1]} (max {MAX_SSIM_PIXELS})"
        )

    if np.array_equal(img1, img2):
        return 1.0

    c1 = (0.01 * data_range) ** 2
    c2 = (0.03 * data_range) ** 2

    # Convert to grayscale if multi-channel by averaging.
    if img1.ndim == 3:
        img1 = img1.mean(axis=2)
        img2 = img2.mean(axis=2)

    # Pad images to handle borders.
    pad = win_size // 2
    img1_p = np.pad(img1, pad, mode="reflect")
    img2_p = np.pad(img2, pad, mode="reflect")

    h, w = img1.shape
    ssim_sum = 0.0
    count = 0

    for i in range(h):
        for j in range(w):
            w1 = img1_p[i : i + win_size, j : j + win_size]
            w2 = img2_p[i : i + win_size, j : j + win_size]

            mu1 = w1.mean()
            mu2 = w2.mean()
            sigma1 = w1.var()
            sigma2 = w2.var()
            sigma12 = ((w1 - mu1) * (w2 - mu2)).mean()

            ssim_val = ((2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)) / (
                (mu1**2 + mu2**2 + c1) * (sigma1 + sigma2 + c2)
            )
            ssim_sum += ssim_val
            count += 1

    return float(ssim_sum / count) if count > 0 else 1.0


def compare_images(
    original: Path | str,
    compared: Path | str,
) -> QualityMetrics:
    """Compare two images and return quality metrics.

    Args:
        original: Path to the original image.
        compared: Path to the image to compare against.

    Returns:
        A :class:`QualityMetrics` with SSIM, PSNR, and MSE.

    Raises:
        FileNotFoundError: If either path does not exist.
        ValueError: If images have different dimensions.

    """
    orig_path = Path(original)
    comp_path = Path(compared)

    if not orig_path.exists():
        raise FileNotFoundError(f"Original image not found: {orig_path}")
    if not comp_path.exists():
        raise FileNotFoundError(f"Compared image not found: {comp_path}")

    arr1 = _load_as_array(orig_path)
    arr2 = _load_as_array(comp_path)

    if arr1.shape != arr2.shape:
        msg = (
            f"Image dimensions don't match: "
            f"{arr1.shape[1]}x{arr1.shape[0]} vs {arr2.shape[1]}x{arr2.shape[0]}"
        )
        raise ValueError(msg)

    mse = compute_mse(arr1, arr2)
    psnr = compute_psnr(mse)
    ssim = compute_ssim(arr1, arr2)

    return QualityMetrics(
        ssim=round(ssim, 4),
        psnr=round(psnr, 2) if psnr is not None else None,
        mse=round(mse, 4),
        original_path=orig_path,
        compared_path=comp_path,
        width=arr1.shape[1],
        height=arr1.shape[0],
    )
