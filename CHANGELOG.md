# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.7] - 2026-07-30

### Added

- Lossless compression mode for PNG/WEBP (`--lossless`).
- Interactive HTML before/after comparison slider (`pixopt compare`).
- Adaptive quality via binary search for target file size (`--target-size`).
- Responsive srcset image generation with HTML snippet output (`pixopt srcset`).
- Lazy-loading placeholders: dominant color, LQIP data URI, and blurhash (`pixopt placeholder`).
- Smart format detection: auto-select WEBP/JPEG/PNG based on image content (`--smart-format`).
- Backup originals before processing (`--backup`).
- Skip files below a minimum size threshold (`--min-size`).
- Animated GIF to animated WEBP conversion.
- Pure-Python SVG minification.
- HEIC/HEIF support via `pillow-heif`.
- GitHub Actions workflows for CI, release (PyPI), and documentation.
- `python -m pixopt.cli` is now supported via `pixopt/cli/__main__.py`.
- Public API (`OutputFormat`, `PlaceholderType`, `SrcsetImage`, and core functions) is exported from the `pixopt` package root.

### Fixed

- Palette image transparency is now flattened to white for JPEG/WEBP correctly.
- SVG optimizer no longer corrupts CDATA/text or removes quotes globally.
- SVG optimizer only removes non-inherited default attributes (`opacity`) and only rounds numeric attributes, preventing corruption of `id`/`class`/`href` values.
- HTML comparison slider embeds images with correct MIME types.
- HTML comparison slider now escapes the title to prevent HTML/XSS injection.
- HTML comparison slider works for SVG before/after images.
- srcset output paths and HTML `src`/`srcset` attributes are consistent.
- Favicon generation preserves or flattens transparency consistently.
- `convert_to_favicon` validates `sizes` (non-empty, positive integers).
- `strip_metadata_pillow` preserves indexed palettes and avoids the deprecated Pillow `getdata()` method.
- `adaptive_quality` rejects invalid target sizes.
- `placeholder` raises a clear error for unsupported placeholder types.
- `generate_lqip_datauri` and `generate_blurhash` validate their numeric inputs.
- `detect_optimal_format` handles corrupt, missing, and oversized files gracefully.
- `resolve_output_format` ensures `AUTO` mode assigns a canonical extension when the output path lacks one.
- `find_quality_for_target_size` validates quality bounds, tolerance and iteration count.
- `srcset` CLI snippet now uses `as_posix()`, URL-encodes special characters and escapes the output for safe HTML.
- Animated images from non-GIF sources are preserved when converted to WEBP.
- `optimize_image` validates that `output_format` is an `OutputFormat` value.
- `discover_images` ignores symlink escapes outside the source directory.
- CLI `info` handles corrupt/unrecognised images and uses faster EXIF lookups.
- CLI `compare` uses a cross-platform file URI for `webbrowser.open`.
- CLI options for `--width`, `--height`, `--target-size`, and `--min-size` reject non-positive values.

### Changed

- Removed legacy metadata files (`setup.py`, `requirements.txt`, `requirements-dev.txt`, `MANIFEST.in`).
- Updated minimum Python requirement to 3.10.
