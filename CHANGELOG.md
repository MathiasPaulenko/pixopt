# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Lossless compression mode for PNG/WEBP (`--lossless`).
- Interactive HTML before/after comparison slider (`optimg compare`).
- Adaptive quality via binary search for target file size (`--target-size`).
- Responsive srcset image generation with HTML snippet output (`optimg srcset`).
- Lazy-loading placeholders: dominant color, LQIP data URI, and blurhash (`optimg placeholder`).
- Smart format detection: auto-select WEBP/JPEG/PNG based on image content (`--smart-format`).
- Backup originals before processing (`--backup`).
- Skip files below a minimum size threshold (`--min-size`).
- Animated GIF to animated WEBP conversion.
- Pure-Python SVG minification.
- HEIC/HEIF support via `pillow-heif`.
- GitHub Actions workflows for CI, release (PyPI), and documentation.
