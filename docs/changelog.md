# Changelog

All notable changes to this project are documented in this file and in the [GitHub Releases](https://github.com/MathiasPaulenko/pixopt/releases) page.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Lossless compression mode** for PNG/WEBP (`--lossless`) — preserves every pixel for UI assets and icons.
- **Interactive HTML before/after comparison slider** (`pixopt compare`) — visually inspect quality differences.
- **Adaptive quality** via binary search for target file size (`--target-size`) — automatically find the best quality for a given file size budget.
- **Responsive srcset image generation** with HTML snippet output (`pixopt srcset`) — generate multi-width variants and `<img srcset="...">` tags.
- **Lazy-loading placeholders** (`pixopt placeholder`) — extract dominant color, LQIP data URI, or blurhash strings.
- **Smart format detection** (`--smart-format`) — auto-select WEBP/JPEG/PNG based on image content analysis.
- **Backup originals** (`--backup`) — copy originals to a backup directory before processing.
- **Min-size filter** (`--min-size`) — skip files already below a size threshold.
- **Animated GIF to animated WEBP** conversion.
- **Pure-Python SVG minification** — no Node.js dependencies required.
- **HEIC/HEIF support** via `pillow-heif` — process iPhone photos natively.
- **Favicon generation** (`pixopt favicon`) — multi-resolution ICO output.
- **Batch processing** (`pixopt batch`) — optimize specific files rather than entire directories.
- **Visual comparison HTML generation** (`pixopt html_comparison`) — programmatic API for comparison sliders.

### Changed

- Improved CLI output with Rich tables and progress indicators.
- Refactored internal image operations for better maintainability.

### Fixed

- Resolved HEIC conversion errors on certain Windows installations.
- Fixed animated GIF frame handling for non-RGBA modes.
- Corrected SVG minification for files with XML namespaces.
