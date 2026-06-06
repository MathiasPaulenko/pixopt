# Changelog

See [CHANGELOG.md](https://github.com/MathiasPaulenko/pixopt/blob/main/CHANGELOG.md) for the full changelog.

## [Unreleased]

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
