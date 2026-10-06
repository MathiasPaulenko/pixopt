# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-08-06

### Fixed

- Preserved transparency (`info["transparency"]`) when rebuilding indexed PNG (`P` mode) images in `strip_metadata_pillow`.
- Preserved all animation frames, durations, and loop count when converting animated GIFs to GIF or WEBP.
- Reapplied save kwargs (quality, optimize, progressive) when resaving images with `keep_exif_groups`.
- Generated unique output names (`_1`, `_2`, ...) in `batch_optimize` and `async_batch_optimize` when sources share a basename.
- Fixed `compare -f webp` crashing on a missing temporary file by deriving the suffix from the real output path.
- Fixed `--preset` being ignored for `quality`, `strip`, `progressive`, `optimize`, and `lossless` in `optimize` and `convert` via tristate option defaults.
- Resolved output format from the output path (not the source) in `_resolve_quality`, fixing `--target-size` combined with `-f` or `--smart-format`.
- Removed the `-s` short-flag collision between `--sizes` and `--strip` in `pixopt srcset`; `-s` now means `--sizes`.
- Kept `--output json` stdout clean by skipping the Rich table in `optimize` and `convert`.
- Validated unknown formats in `generate_srcset_images` (raises `ValueError` instead of silently falling back to WEBP), `nextgen -f`/`-q`, and `compute_ssim` `win_size`/`data_range`.
- Enforced `MAX_SCAN_ENTRIES` over all discovered files, not only valid images, and guarded a `stat()` race in `scan_directory`.
- Matched `async_optimize_image` error behavior to the sync API and fixed `ProgressInfo.current` to report completed files.
- Hardened `pdf_io` against large PDFs (`MAX_PDF_TOTAL_PIXELS`), `RuntimeError` from PyMuPDF, and deprecated `import fitz` (now `import pymupdf` with fallback).
- Closed intermediate Pillow images in `palette`, `placeholder`, `benchmark`, `perceptual`, `sprite`, and `quality` helpers.
- Applied the `background` color when flattening RGBA/palette images in `sprite` cells.
- Added exception handling to the `placeholder` and `nextgen` CLI commands and path validation to `scan_duplicates`.
- Removed a stale `type: ignore` in `optimizer.py` that broke `mypy --strict`.

### Changed

- Corrected `README.md` Quick Start and recipes that omitted the required output path.
- Fixed incorrect examples in `docs/cli.md` (`batch --fit`), `docs/library.md` (`variant.label`, `min_size` check), and `docs/advanced.md` (`apply_preset` override keys, missing import).
- Expanded `docs/api.md` with previously undocumented public types (presets, EXIF, exceptions, palette, benchmark, progress, result dataclasses).
- Updated `SECURITY.md` supported versions to include the `1.2.x` line.
- Corrected the `find_quality_for_target_size` docstring ("closest to the target") and `mypy` configuration for the `pymupdf` module.

## [1.2.1] - 2026-08-01

### Changed

- Expanded MkDocs documentation with comprehensive CLI, library and advanced usage guides.
- Updated README with missing CLI commands, features and library examples.
- Formatted Markdown code examples with ruff.
- Added PyPI trusted-publishing release workflow.

## [1.2.0] - 2026-07-31

### Fixed

- Fixed `inventory.py` `smallest_size` logic and narrowed exception handling.
- Fixed division-by-zero and invalid-dimension guards in `image_ops.py`, `watermark.py`, and `sprite.py`.
- Hardened `_open_image` in `image_ops.py` to open a binary file handle and use `os.fstat`, removing a TOCTOU race between size checks and opening.
- Replaced `source_path.exists()` / `source_path.stat()` checks in `optimizer.py` with a single `try/except stat()` call.
- Hardened `presets.py` value validation for `fit`, `anchor`, `background-color`, `format`, and numeric bounds.
- Validated `watermark` path in `add_image_watermark` and `font_path` access with `try/except stat()`.
- Ensured image resources created by watermark, placeholder, favicon conversion, PDF import, and benchmark AVIF checks are closed.
- Fixed `async_batch_optimize` to propagate progress-callback exceptions and convert unexpected `asyncio.gather` exceptions into `OptimizationResult` objects.
- Added `validate_no_parent_references` for `benchmark` source, `inventory` directories, and `pipeline` source paths.
- Replaced `Path.exists()` / `Path.stat()` checks with `try/except stat()` in `benchmark`, `inventory`, and `nextgen`.
- Ensured `sprite.py`, `pdf_io.py`, and `optimizer.py` close all opened image resources in `finally` blocks.
- Fixed `pipeline.py` `save()` to validate output paths and use the system temp directory for watermark temporary files.

### Changed

- Pinned `mkdocs-material` to `<9.7.0` in docs dependencies to avoid a broken upstream release that emits non-actionable warnings and causes `mkdocs build --strict` to fail.
- Corrected smart-format examples in `README.md` and `docs/cli.md` to use an explicit output file (`output.webp`) rather than a directory.
- Fixed `docs/library.md` `PipelineResult` example to reference `size_bytes` and guard against a zero success count.
- Fixed `README.md` `optimize` example to include an explicit output file so `--smart-format` is valid without `--overwrite`.
- Restored `mkdocs build --strict` in CI/docs workflows.
- Removed invalid `--smart-format` flag from the `pixopt batch` example in `docs/cli.md`.
- Fixed `base64_to_image` and `optimize_base64` to handle invalid base64 input gracefully by raising `ValueError` or returning an error result instead of leaking `binascii.Error`.

### Added

- Regression tests for inventory empty scans, aspect-ratio validation, watermark text length and invalid dimensions, async progress callbacks, and invalid preset values.

## [1.1.1] - 2026-07-31

### Fixed

- Corrected CLI `--auto-orient`/`--keep-orientation` handling when used with presets: explicit flags now properly override preset values.
- Fixed mypy strict-mode errors across the package (Image/ImageFile assignments, missing generic type arguments, protocol call signatures, union return types).
- Removed all ruff lint and formatting violations.
- Fixed `async_batch_optimize` progress callback to use `ProgressInfo`.
- Fixed `batch_optimize` parameter defaults and forwarding to `optimize_image`.
- Hardened `pipeline.py` watermark steps to remove temporary files even when an operation fails.
- Added fast exact-duplicate detection path in `find_duplicates` for `threshold=0`, reducing worst-case complexity from O(n²) to O(n log n).
- Added early-exit for identical images in `compute_ssim` to avoid unnecessary sliding-window work.

### Added

- Made PyMuPDF (`fitz`) an optional dependency; PDF tests skip when it is unavailable.
- Added input and resource limits for safety: max input/base64/preset/PDF sizes, max PDF pages, max image dimensions, and max srcset widths.
- Added validation for font files and image dimensions in watermark operations.
- Added output path escape validation in `optimize_directory`.
- Added `MAX_INPUT_BYTES` guard in `optimize_image`.
- Added image-dimension validation (`MAX_IMAGE_DIMENSION`) to `optimize_image`, `convert_to_favicon`, `optimize_bytes`, `smart_format`, and `placeholder`.
- Hardened path handling: `output`, `backup_dir`, and `output_dir` in `optimize_image`, `optimize_directory`, `batch_optimize`, and `async_batch_optimize` now reject parent-directory references.
- Fixed PDF resource leak in `pdf_io.py` and ensure the `fitz` document is always closed.
- Fixed `bytes_to_image` and `base64_to_image` to load and close the image before returning it, avoiding resource leaks while keeping the image usable.
- Fixed `pipeline.py` resource leaks by using `Image.open` context managers and closing the final image.
- Fixed `SVG` attribute parsing to handle the case where no capture group matches.
- Fixed `format_resolver` for in-memory images without a filename or with unknown formats.
- Made `WHITE` constant canonical and removed duplicates in `io_bytes.py` and `sprite.py`.
- Added missing CLI command imports in `pixopt.cli.commands.__init__`.
- Added missing public API symbols (`load_custom_presets`, `find_quality_for_target_size`, `StructuredFormatter`) to `pixopt.__all__`.
- Added `__all__` declarations to `constants.py`, `utils.py`, `svg_optimizer.py`, `image_ops.py`, `inspect.py`, and `presets.py`.
- Added `numpy` to core dependencies and `PyMuPDF` optional dependency for `pdf`.
- Added input validation and resource limits across public APIs:
  - `BundleOptions` validates dimensions, quality, palette count, srcset/favicon sizes.
  - `create_sprite` and `create_contact_sheet` validate cell/column/padding dimensions.
  - `pdf_to_images` validates `dpi` against `MAX_PDF_DPI`.
  - Perceptual hashing validates resize size against `MAX_HASH_SIZE` and caps duplicate scan length with `MAX_DUPLICATE_SCAN`.
  - `generate_blurhash` and `generate_lqip_datauri` validate component counts and dimensions.
- Added `MAX_BLURHASH_COMPONENTS`, `MAX_BUNDLE_PALETTE_N`, `MAX_DUPLICATE_SCAN`, `MAX_HASH_SIZE`, and `MAX_PDF_DPI` to `pixopt._units`.
- Hardened CLI option validation with Typer `min`/`max` constraints and in-function checks for `bundle`, `sprite`, `pdf`, `placeholder`, `srcset`, and `duplicates` commands.
- Centralized path-traversal protection in `pixopt.utils.validate_no_parent_references` and applied it across `optimizer`, `bundle`, `sprite`, `pdf_io`, `srcset_generator`, `html_comparison`, `nextgen`, `pipeline`, `watermark`, and all CLI commands that create directories or write files.
- Added regression tests for path traversal, oversized dimensions, invalid `max_concurrency`, and malformed SVG attributes.
- Added resource limits to prevent unbounded memory in animated GIF conversion (`MAX_GIF_FRAMES`, `MAX_GIF_TOTAL_PIXELS`).
- Added `MAX_SPRITE_IMAGES`, `MAX_FAVICON_SIZES`, and sprite/contact-sheet/favicon dimension limits.
- Avoided full-resolution copies during favicon generation.
- Added `MAX_HTML_BASE64_BYTES` limit in HTML comparison generator.
- Added per-width validation to `generate_srcset_images`.
- Added `MAX_INPUT_BYTES` guards to perceptual hashing and quality comparison.
- Centralized image opening in a private `_open_image` context manager that applies path-traversal, size, dimension, and decompression-bomb guards everywhere images are loaded.
- Hardened `pipeline.py` watermark font/watermark paths and preset file path against parent-directory references.
- Replaced predictable pipeline watermark temp file names with `tempfile.mkstemp`.
- Added resource budgets: `MAX_SSIM_PIXELS`, `MAX_NEAR_DUPLICATE_SCAN`, `MAX_SPRITE_TOTAL_PIXELS`, `MAX_PDF_IMAGES`/`MAX_PDF_TOTAL_PIXELS`, `MAX_SCAN_ENTRIES`, and `MAX_DIRECTORY_SCAN`.
- Added `MAX_IMAGE_DIMENSION` validation to PDF import.
- Hardened watermark input validation for `padding`, `font_size`, and `scale`.
- Hardened `phash` `highfreq_factor` validation.
- Expanded regression tests for path traversal, resource limits, font validation, and format resolver/SVG edge cases.
- Made `validate_optimize_params` a public API.
- Converted `PlaceholderType` to an `Enum` for consistency with other public types and updated the CLI `placeholder` command to use it.
- Added `__version__` to the public `__all__` exports.
- Added smart-format helpers (`has_transparency`, `count_unique_colors`, `is_photo`) to public exports.
- Added `Base64Result` dataclass for typed base64 optimization results and updated tests to use it.
- Updated package metadata to PEP 639 license format and added Python 3.13/3.14 classifiers.
- Updated `numpy` lower bound to `>=2.0.0` for Python 3.14 compatibility.

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
