"""Perceptual hashing and duplicate detection.

Provides ``phash``, ``dhash``, ``ahash`` for finding similar or duplicate
images.  Useful for galleries and asset management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter

from pixopt._units import MAX_DUPLICATE_SCAN, MAX_HASH_SIZE, MAX_NEAR_DUPLICATE_SCAN
from pixopt.image_ops import _open_image, _pixel_data
from pixopt.logging import get_logger
from pixopt.utils import discover_images, validate_no_parent_references

__all__ = [
    "HashResult",
    "DuplicateGroup",
    "DuplicateReport",
    "ahash",
    "dhash",
    "phash",
    "compute_hash",
    "hamming_distance",
    "find_duplicates",
    "scan_duplicates",
]

_logger = get_logger("perceptual")

_DEFAULT_HASH_SIZE = 8


@dataclass(frozen=True)
class HashResult:
    """Result of computing a perceptual hash on an image."""

    file_path: Path
    algorithm: str
    hash_hex: str
    hash_size: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "algorithm": self.algorithm,
            "hash_hex": self.hash_hex,
            "hash_size": self.hash_size,
        }


@dataclass
class DuplicateGroup:
    """A group of images that are duplicates or near-duplicates."""

    hash_hex: str
    algorithm: str
    files: list[Path] = field(default_factory=list)
    distances: dict[str, int] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.files)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hash_hex": self.hash_hex,
            "algorithm": self.algorithm,
            "files": [str(f) for f in self.files],
            "count": self.count,
        }


@dataclass
class DuplicateReport:
    """Report of all duplicate groups found in a scan."""

    directory: Path
    algorithm: str
    threshold: int
    total_files: int
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)
    total_duplicates: int = 0

    @property
    def has_duplicates(self) -> bool:
        return len(self.duplicate_groups) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "directory": str(self.directory),
            "algorithm": self.algorithm,
            "threshold": self.threshold,
            "total_files": self.total_files,
            "duplicate_groups": [g.to_dict() for g in self.duplicate_groups],
            "total_duplicates": self.total_duplicates,
        }


# ---------------------------------------------------------------------------
# Hashing functions
# ---------------------------------------------------------------------------


def _img_to_grayscale(source: Path | str, size: int) -> Image.Image:
    """Open image, convert to grayscale, and resize to size×size."""
    if size < 1 or size > MAX_HASH_SIZE:
        raise ValueError(f"Hash resize size must be 1-{MAX_HASH_SIZE}, got {size}")
    image: Image.Image
    with _open_image(source, label="source") as img:
        image = img.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    # ``image`` is a newly allocated core; the caller is responsible for closing it.
    return image


def ahash(source: Path | str, *, hash_size: int = _DEFAULT_HASH_SIZE) -> str:
    """Compute the average hash (aHash) of an image.

    The image is resized to ``hash_size × hash_size`` grayscale, then each
    pixel is compared to the mean: above → 1, below → 0.

    Returns:
        A hex string representing the hash.
    """
    img = _img_to_grayscale(source, hash_size)
    try:
        pixels = _pixel_data(img)
        avg = sum(pixels) / len(pixels) if pixels else 0
        bits = [1 if p >= avg else 0 for p in pixels]
        return _bits_to_hex(bits)
    finally:
        img.close()


def dhash(source: Path | str, *, hash_size: int = _DEFAULT_HASH_SIZE) -> str:
    """Compute the difference hash (dHash) of an image.

    Compares each pixel to its right neighbor: left < right → 1.

    Returns:
        A hex string representing the hash.
    """
    img = _img_to_grayscale(source, hash_size)
    try:
        pixels = _pixel_data(img)
        width = hash_size
        bits = []
        for row in range(hash_size):
            for col in range(hash_size - 1):
                left = pixels[row * width + col]
                right = pixels[row * width + col + 1]
                bits.append(1 if left < right else 0)
        return _bits_to_hex(bits)
    finally:
        img.close()


def phash(
    source: Path | str, *, hash_size: int = _DEFAULT_HASH_SIZE, highfreq_factor: int = 4
) -> str:
    """Compute the perceptual hash (pHash) of an image.

    Uses a DCT-based approach: resize to ``hash_size * highfreq_factor``,
    apply a slight blur, compute the DCT, and take the low-frequency
    components compared to the median.

    Returns:
        A hex string representing the hash.
    """

    if highfreq_factor < 1 or highfreq_factor > 16:
        raise ValueError(f"highfreq_factor must be between 1 and 16, got {highfreq_factor}")

    img_size = hash_size * highfreq_factor
    img = _img_to_grayscale(source, img_size)
    try:
        filtered = img.filter(ImageFilter.MedianFilter(size=3))
        img.close()
        img = filtered
        pixels = _pixel_data(img)

        # Compute 1D DCT for each row, then for each column.
        dct_matrix = _compute_dct_2d(pixels, img_size, img_size)

        # Take the top-left hash_size × hash_size low-frequency block.
        low_freq = []
        for row in range(hash_size):
            for col in range(hash_size):
                low_freq.append(dct_matrix[row * img_size + col])

        # Compare to median (excluding the DC component at [0,0]).
        tail = low_freq[1:]
        median = sorted(tail)[len(tail) // 2] if tail else low_freq[0] if low_freq else 0
        bits = [1 if v > median else 0 for v in low_freq]
        return _bits_to_hex(bits)
    finally:
        img.close()


def _compute_dct_2d(pixels: list[int], width: int, height: int) -> list[float]:
    """Compute a simplified 2D DCT."""
    import math

    # 1D DCT on rows.
    row_dct: list[float] = []
    for y in range(height):
        row = pixels[y * width : (y + 1) * width]
        for k in range(width):
            s = 0.0
            for n in range(width):
                s += row[n] * math.cos(math.pi * k * (2 * n + 1) / (2 * width))
            row_dct.append(s)

    # 1D DCT on columns of the row-transformed data.
    result: list[float] = [0.0] * (width * height)
    for x in range(width):
        col = [row_dct[y * width + x] for y in range(height)]
        for k in range(height):
            s = 0.0
            for n in range(height):
                s += col[n] * math.cos(math.pi * k * (2 * n + 1) / (2 * height))
            result[k * width + x] = s

    return result


def _bits_to_hex(bits: list[int]) -> str:
    """Convert a list of 0/1 bits to a hex string."""
    num = 0
    for bit in bits:
        num = (num << 1) | bit
    hex_len = (len(bits) + 3) // 4
    return format(num, f"0{hex_len}x")


def _hex_to_bits(hex_str: str) -> list[int]:
    """Convert a hex string back to a list of bits."""
    num = int(hex_str, 16)
    bit_len = len(hex_str) * 4
    return [(num >> i) & 1 for i in range(bit_len - 1, -1, -1)]


# ---------------------------------------------------------------------------
# Distance and comparison
# ---------------------------------------------------------------------------


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """Compute the Hamming distance between two hex hash strings.

    Returns:
        The number of differing bits.  0 means identical.
    """
    if not hash_a or not hash_b:
        raise ValueError("hash strings cannot be empty")
    bits_a = _hex_to_bits(hash_a)
    bits_b = _hex_to_bits(hash_b)
    if len(bits_a) != len(bits_b):
        # Pad shorter with zeros
        max_len = max(len(bits_a), len(bits_b))
        bits_a = bits_a + [0] * (max_len - len(bits_a))
        bits_b = bits_b + [0] * (max_len - len(bits_b))
    return sum(a != b for a, b in zip(bits_a, bits_b, strict=True))


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def compute_hash(
    source: Path | str,
    *,
    algorithm: str = "phash",
    hash_size: int = _DEFAULT_HASH_SIZE,
) -> HashResult:
    """Compute a perceptual hash of an image.

    Args:
        source: Path to the image file.
        algorithm: One of ``"phash"``, ``"dhash"``, ``"ahash"``.
        hash_size: Hash size in bits per side (default 8 → 64-bit hash).

    Returns:
        A :class:`HashResult` with the computed hash.

    """
    algorithm = algorithm.lower()
    if algorithm == "phash":
        h = phash(source, hash_size=hash_size)
    elif algorithm == "dhash":
        h = dhash(source, hash_size=hash_size)
    elif algorithm == "ahash":
        h = ahash(source, hash_size=hash_size)
    else:
        raise ValueError(
            f"Unknown hash algorithm: {algorithm!r}. Use 'phash', 'dhash', or 'ahash'."
        )

    return HashResult(
        file_path=Path(source),
        algorithm=algorithm,
        hash_hex=h,
        hash_size=hash_size,
    )


def find_duplicates(
    hashes: list[HashResult],
    *,
    threshold: int = 5,
) -> list[DuplicateGroup]:
    """Find duplicate or near-duplicate images from a list of hashes.

    Args:
        hashes: List of :class:`HashResult` objects.
        threshold: Maximum Hamming distance to consider images as duplicates.

    Returns:
        A list of :class:`DuplicateGroup` objects, each containing files
        that are within ``threshold`` of each other.

    """
    if not hashes:
        return []

    limit = MAX_DUPLICATE_SCAN if threshold == 0 else MAX_NEAR_DUPLICATE_SCAN
    if len(hashes) > limit:
        raise ValueError(f"Too many hashes to compare (max {limit}), got {len(hashes)}")

    groups: list[DuplicateGroup] = []

    if threshold == 0:
        # Fast path for exact duplicates: O(n log n) sort and group.
        sorted_hashes = sorted(hashes, key=lambda h: (h.algorithm, h.hash_hex))
        i = 0
        while i < len(sorted_hashes):
            j = i + 1
            while (
                j < len(sorted_hashes)
                and sorted_hashes[j].algorithm == sorted_hashes[i].algorithm
                and sorted_hashes[j].hash_hex == sorted_hashes[i].hash_hex
            ):
                j += 1
            if j - i > 1:
                groups.append(
                    DuplicateGroup(
                        hash_hex=sorted_hashes[i].hash_hex,
                        algorithm=sorted_hashes[i].algorithm,
                        files=[h.file_path for h in sorted_hashes[i:j]],
                    )
                )
            i = j
        return groups

    assigned: set[int] = set()

    for i, h in enumerate(hashes):
        if i in assigned:
            continue

        group = DuplicateGroup(hash_hex=h.hash_hex, algorithm=h.algorithm, files=[h.file_path])
        assigned.add(i)

        for j in range(i + 1, len(hashes)):
            if j in assigned:
                continue
            if hashes[j].algorithm != h.algorithm:
                continue
            dist = hamming_distance(h.hash_hex, hashes[j].hash_hex)
            if dist <= threshold:
                group.files.append(hashes[j].file_path)
                group.distances[str(hashes[j].file_path)] = dist
                assigned.add(j)

        if group.count > 1:
            groups.append(group)

    return groups


def scan_duplicates(
    directory: Path | str,
    *,
    algorithm: str = "phash",
    threshold: int = 5,
    recursive: bool = False,
    hash_size: int = _DEFAULT_HASH_SIZE,
) -> DuplicateReport:
    """Scan a directory for duplicate or near-duplicate images.

    Args:
        directory: Directory to scan.
        algorithm: Hash algorithm: ``"phash"``, ``"dhash"``, or ``"ahash"``.
        threshold: Maximum Hamming distance for duplicates.
        recursive: Scan subdirectories recursively.
        hash_size: Hash size per side.

    Returns:
        A :class:`DuplicateReport` with all duplicate groups found.

    Raises:
        FileNotFoundError: If the directory does not exist.

    """
    dir_path = Path(directory)
    if error := validate_no_parent_references(dir_path, "directory"):
        raise ValueError(error)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    _logger.debug(
        "Scanning for duplicates", extra={"operation": "duplicates", "path": str(dir_path)}
    )

    limit = MAX_DUPLICATE_SCAN if threshold == 0 else MAX_NEAR_DUPLICATE_SCAN
    hashes: list[HashResult] = []
    for file_path in discover_images(dir_path, recursive=recursive):
        if len(hashes) >= limit:
            _logger.warning(
                "Duplicate scan stopped after reaching the limit",
                extra={"operation": "duplicates", "limit": limit},
            )
            break
        try:
            h = compute_hash(file_path, algorithm=algorithm, hash_size=hash_size)
            hashes.append(h)
        except (OSError, ValueError, Image.DecompressionBombError):
            _logger.warning(
                "Failed to hash", extra={"operation": "duplicates", "path": str(file_path)}
            )

    groups = find_duplicates(hashes, threshold=threshold)

    report = DuplicateReport(
        directory=dir_path,
        algorithm=algorithm,
        threshold=threshold,
        total_files=len(hashes),
        duplicate_groups=groups,
        total_duplicates=sum(g.count for g in groups),
    )

    _logger.info(
        "Duplicate scan complete",
        extra={"operation": "duplicates", "path": str(dir_path), "size_bytes": len(groups)},
    )

    return report
