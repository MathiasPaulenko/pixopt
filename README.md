# pixopt

*A powerful, easy-to-use Python library and CLI tool for optimizing images for web and storage.*

[![PyPI version](https://img.shields.io/pypi/v/pixopt)](https://pypi.org/project/pixopt/)
[![Python versions](https://img.shields.io/pypi/pyversions/pixopt)](https://pypi.org/project/pixopt/)
[![CI status](https://img.shields.io/github/actions/workflow/status/MathiasPaulenko/pixopt/ci.yml?label=CI)](https://github.com/MathiasPaulenko/pixopt/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/codecov/c/github/MathiasPaulenko/pixopt)](https://codecov.io/gh/MathiasPaulenko/pixopt)
[![License](https://img.shields.io/github/license/MathiasPaulenko/pixopt)](https://github.com/MathiasPaulenko/pixopt/blob/main/LICENSE)

[📖 Documentation](https://mathiaspaulenko.github.io/pixopt/) •
[📦 PyPI](https://pypi.org/project/pixopt/) •
[🏷️ Releases](https://github.com/MathiasPaulenko/pixopt/releases)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
  - [Requirements](#requirements)
  - [From PyPI](#from-pypi)
  - [With HEIC/HEIF support](#with-heicheif-support)
  - [With PDF support](#with-pdf-support)
  - [From source](#from-source)
  - [Verify installation](#verify-installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
  - [Commands](#commands)
  - [Global Options](#global-options)
  - [Use-Case Recipes](#use-case-recipes)
- [Library Usage](#library-usage)
  - [Basic optimization](#basic-optimization)
  - [Batch processing](#batch-processing)
  - [Format conversion](#format-conversion)
  - [Lossless compression](#lossless-compression)
  - [Adaptive quality](#adaptive-quality)
  - [Placeholders](#placeholders)
  - [Smart format detection](#smart-format-detection)
  - [Responsive srcset](#responsive-srcset)
  - [Backup and min-size filter](#backup-and-min-size-filter)
  - [Favicon generation](#favicon-generation)
  - [Watermarking](#watermarking)
  - [Sprite sheets](#sprite-sheets)
  - [Asset bundles](#asset-bundles)
  - [PDF export](#pdf-export)
  - [Next-gen formats](#next-gen-formats)
  - [Base64 and bytes I/O](#base64-and-bytes-io)
- [API Reference](#api-reference)
- [Development](#development)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Acknowledgements](#acknowledgements)
- [License](#license)

---

## Overview

**pixopt** is a fast Python image optimizer designed for modern web workflows. It provides both a rich **command-line interface (CLI)** and a clean **Python API** to resize, compress, convert formats, generate responsive assets, extract lazy-loading placeholders, and detect the optimal format automatically.

Whether you are a developer automating image pipelines, a designer preparing assets, or a DevOps engineer optimizing static sites, pixopt handles the heavy lifting so you don't have to.

---

## Features

- 🖼️ **Format conversion** — JPEG, PNG, WEBP, AVIF, GIF, HEIC/HEIF, SVG
- 🎞️ **Animated GIF → WEBP** — convert animated GIFs to much lighter animated WEBP
- 🧹 **SVG minification** — pure-Python SVG cleanup (no Node.js tools needed)
- 📱 **HEIC/HEIF import** — open iPhone photos directly via `pillow-heif`
- 🎯 **Lossless mode** — lossless PNG/WEBP compression for UI assets that need pixel-perfect fidelity
- 🔍 **Adaptive quality** — binary-search quality to hit a target file size automatically
- 📊 **Visual comparison** — generate interactive HTML before/after sliders
- 📐 **Responsive srcset** — generate multiple width variants and HTML `<img srcset="...">` snippets
- 🎨 **Lazy-loading placeholders** — extract dominant color, generate LQIP data URIs, or blurhash strings
- 🧠 **Smart format detection** — auto-detect the most efficient format (photo → WEBP, graphic → PNG, transparent → WEBP)
- 💾 **Backup originals** — copy originals to a backup directory before processing
- ⚡ **Batch processing** — optimize single files, directories, or multiple files at once
- 💧 **Watermarking** — add text or image watermarks with position, opacity and scaling
- 🧩 **Sprite sheets & contact sheets** — pack images into CSS sprites or visual contact sheets
- 📦 **Asset bundles** — generate ready-to-deploy asset packages for the web
- 📄 **PDF import/export** — extract pages as images or bundle images into PDFs
- 🚀 **Next-gen formats** — produce JXL and WebP2 outputs
- 🔎 **Duplicate detection** — find visually or exactly similar images
- 📁 **Directory scanning** — scan folders and produce inventory reports with aggregate statistics
- 🥊 **Format benchmark** — compare size/quality across JPEG, PNG, WEBP, AVIF
- 🎨 **Color palette** — extract dominant color swatches from images
- 🌊 **Async API** — async versions of all major operations
- 🔡 **Base64 & bytes I/O** — optimize in-memory images for APIs and web services
- 🔐 **Safety hardening** — path validation, input limits, and resource leak protection
- 💻 **Beautiful CLI** — built with Typer for an intuitive command-line experience

---

## Installation

### Requirements

- **Python**: 3.10, 3.11, 3.12, 3.13, or 3.14
- **Core dependencies**: Pillow (>=12.3.0), pillow-heif, typer, rich, piexif, numpy
- **Optional**: PyMuPDF for PDF import/export (`pip install pixopt[pdf]`)

### From PyPI

```bash
pip install pixopt
```

### With HEIC/HEIF support

`pillow-heif` is included as a core dependency, so HEIC/HEIF support is available out of the box.

```bash
pip install pixopt
```

### With PDF support

```bash
pip install "pixopt[pdf]"
```

### From source

```bash
git clone https://github.com/MathiasPaulenko/pixopt.git
cd pixopt
pip install -e ".[dev,docs]"
```

### Verify installation

```bash
pixopt --help
```

---

## Quick Start

### CLI

```bash
pip install pixopt
pixopt optimize photo.jpg photo_optimized.jpg --quality 80 --width 1200
```

### Library

```python
from pixopt import optimize_image
from pixopt.models import OutputFormat

result = optimize_image(
    "photo.jpg",
    "photo_optimized.webp",
    max_width=1200,
    quality=80,
    output_format=OutputFormat.WEBP,
)
print(f"Saved {result.savings_percent:.1f}%")
```

---

## CLI Usage

The CLI is built with [Typer](https://typer.tiangolo.com/) and provides an intuitive interface for all optimization features.

### Commands

#### `optimize`

Optimize a single image or all images in a directory.

```bash
pixopt optimize photo.jpg photo_optimized.jpg --quality 80 --width 1200
pixopt optimize ./images ./optimized --recursive --quality 85 --format webp
```

#### `batch`

Optimize multiple specific files at once.

```bash
pixopt batch photo1.jpg photo2.png photo3.bmp -o ./optimized --width 800
```

#### `convert`

Convert an image to a different format or extension.

```bash
pixopt convert photo.png photo.webp -f webp
pixopt convert ./images ./webp_images -r -f webp
```

#### `favicon`

Convert an image to a multi-resolution ICO favicon.

```bash
pixopt favicon logo.png favicon.ico
pixopt favicon logo.png favicon.ico --size 16 --size 32 --size 48
```

#### `info`

Inspect image metadata without optimizing.

```bash
pixopt info photo.jpg
```

#### `compare`

Generate an interactive HTML before/after slider.

```bash
pixopt compare photo.jpg comparison.html --open
```

#### `srcset`

Generate responsive image variants and an HTML srcset snippet.

```bash
pixopt srcset hero.jpg --sizes 320,640,1024,1920 --output-dir ./responsive/
pixopt srcset hero.jpg --sizes 320,640,1024,1920 -f webp --html snippet.html
```

#### `placeholder`

Extract a placeholder for lazy loading (color, LQIP, or blurhash).

```bash
pixopt placeholder photo.jpg --type color
pixopt placeholder photo.jpg --type lqip
pixopt placeholder photo.jpg --type blurhash -o blurhash.txt
```

#### `watermark`

Add text or image watermarks.

```bash
pixopt watermark photo.jpg watermarked.jpg --text "© 2026"
pixopt watermark photo.jpg watermarked.jpg --watermark-image logo.png --position bottom-right --opacity 0.5
```

#### `sprite`

Pack images into a sprite or contact sheet.

```bash
pixopt sprite sprite.png icon1.png icon2.png icon3.png
pixopt sprite contact.jpg ./thumbnails/* --contact-sheet
```

#### `bundle`

Generate a ready-to-deploy asset bundle from a source image.

```bash
pixopt bundle photo.jpg -o ./bundle
```

#### `pdf`

Import PDF pages as images or export images as a PDF.

```bash
pixopt pdf document.pdf -o ./pages
pixopt pdf output.pdf --from-images page1.jpg --from-images page2.jpg
```

#### `nextgen`

Convert images to next-generation JXL or WebP2.

```bash
pixopt nextgen detect
pixopt nextgen convert photo.jpg -o photo.jxl -f jxl
```

#### `duplicates`

Find duplicate or visually similar images.

```bash
pixopt duplicates ./images --threshold 10
```

#### `scan`

Scan a directory and report optimization potential.

```bash
pixopt scan ./images --recursive
```

#### `benchmark`

Compare size/quality across formats.

```bash
pixopt benchmark photo.jpg --format JPEG --format WEBP --format AVIF
```

#### `palette`

Extract a color palette from an image.

```bash
pixopt palette photo.jpg --count 5
```

#### `metrics`

Compute PSNR/SSIM quality metrics between two images.

```bash
pixopt metrics original.jpg optimized.jpg
```

### Global Options

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `--quality` | `-q` | JPEG/WEBP quality (1-100) | `85` |
| `--width` | `-w` | Maximum width in pixels | — |
| `--height` | `-h` | Maximum height in pixels | — |
| `--format` | `-f` | Output format: auto, jpeg, png, webp, avif, original | `auto` |
| `--strip` | `-s` | Remove metadata | `True` |
| `--progressive` | — | Progressive JPEG encoding | `True` |
| `--recursive` | `-r` | Process directories recursively | `False` |
| `--overwrite` | — | Overwrite source files | `False` |
| `--lossless` | — | Lossless PNG/WEBP compression | `False` |
| `--target-size` | — | Target file size in KB (adaptive quality) | — |
| `--smart-format` | — | Auto-detect the most efficient output format | `False` |
| `--backup` | — | Backup originals to this directory | — |
| `--min-size` | — | Skip files already smaller than this threshold (KB) | — |

### Use-Case Recipes

#### Lossless PNG/WEBP for UI assets

```bash
pixopt convert icon.png icon.webp --lossless -f webp
```

#### Target a specific file size

```bash
pixopt optimize photo.jpg photo_optimized.jpg --target-size 50
```

#### Auto-detect the output format

```bash
pixopt optimize photo.jpg photo_optimized.jpg --smart-format
pixopt convert graphic.png output.webp --smart-format
```

#### Backup originals before processing

```bash
pixopt optimize ./images ./optimized --backup ./originals --recursive
```

#### Skip already-optimized files

```bash
pixopt optimize ./images ./optimized --min-size 10 --recursive
```

#### Animated GIF to animated WEBP

```bash
pixopt convert animation.gif animation.webp -f webp
```

#### Convert HEIC (iPhone) to JPEG

```bash
pixopt convert photo.heic photo.jpg
```

#### Optimize SVG

```bash
pixopt convert icon.svg icon.min.svg
```

---

## Library Usage

pixopt can be used as a Python library for custom workflows and integrations.

### Basic optimization

```python
from pixopt import optimize_image
from pixopt.models import OutputFormat

result = optimize_image(
    "photo.jpg",
    "photo_optimized.webp",
    max_width=1200,
    quality=80,
    strip_metadata=True,
    output_format=OutputFormat.WEBP,
)

print(f"Saved {result.savings_percent:.1f}% ({result.human_savings})")
print(f"Output: {result.output_path}")
```

### Batch processing

```python
from pixopt import optimize_directory
from pixopt.models import OutputFormat

results = optimize_directory(
    "./images",
    "./optimized",
    recursive=True,
    max_width=800,
    quality=75,
    output_format=OutputFormat.WEBP,
)

for r in results:
    if r.success:
        print(f"{r.source_path.name}: {r.savings_percent:.1f}% saved")
    else:
        print(f"{r.source_path.name}: failed — {r.error}")
```

### Format conversion

```python
from pixopt import optimize_image
from pixopt.models import OutputFormat

result = optimize_image(
    "icon.png",
    "icon.webp",
    output_format=OutputFormat.WEBP,
    lossless=True,
)
```

### Lossless compression

```python
from pixopt import optimize_image
from pixopt.models import OutputFormat

result = optimize_image(
    "ui_asset.png",
    "ui_asset.webp",
    output_format=OutputFormat.WEBP,
    lossless=True,
)
```

### Adaptive quality

```python
from PIL import Image
from pixopt import optimize_image
from pixopt.adaptive_quality import find_quality_for_target_size
from pixopt.models import OutputFormat

with Image.open("photo.jpg") as img:
    img.load()
    quality = find_quality_for_target_size(img, "JPEG", target_size=50 * 1024)

result = optimize_image(
    "photo.jpg",
    "photo_optimized.jpg",
    output_format=OutputFormat.JPEG,
    quality=quality,
)

print(f"Use quality {quality}")
```

### Placeholders

```python
from pixopt.placeholder import generate_placeholder

# Dominant color
color = generate_placeholder("photo.jpg", placeholder_type="color")
# → "#3f7a8c"

# Low-quality image placeholder (base64 data URI)
lqip = generate_placeholder("photo.jpg", placeholder_type="lqip")
# → "data:image/jpeg;base64,/9j/4AAQ..."

# Blurhash-style string (custom compact encoding, not the official BlurHash format)
blurhash = generate_placeholder("photo.jpg", placeholder_type="blurhash")
# → "LEHV6nWB2yk8pyo0adR*.7kCMdnj"
```

### Smart format detection

```python
from pixopt.smart_format import detect_optimal_format

fmt = detect_optimal_format("photo.jpg")
# Returns OutputFormat.WEBP for photos, PNG for graphics, WEBP for transparent images
```

### Responsive srcset

```python
from pixopt.srcset_generator import generate_srcset_images

variants = generate_srcset_images(
    "hero.jpg",
    "./responsive",
    widths=[320, 640, 1024, 1920],
    output_format="WEBP",
    quality=80,
)

for v in variants:
    print(f"{v.width}px -> {v.size_bytes} bytes")
```

### Backup and min-size filter

```python
from pixopt import optimize_image

result = optimize_image(
    "photo.jpg",
    "photo_optimized.jpg",
    quality=75,
    backup_dir="./backups",
    min_size_bytes=10240,  # Skip files below 10 KB
)
```

### Favicon generation

```python
from pixopt.optimizer import convert_to_favicon

result = convert_to_favicon(
    "logo.png",
    "favicon.ico",
    sizes=[16, 32, 48],
)
```

### Watermarking

```python
from pixopt import add_text_watermark, add_image_watermark

add_text_watermark(
    "photo.jpg",
    "watermarked.jpg",
    "© 2026",
    position="bottom-right",
)

add_image_watermark(
    "photo.jpg",
    "watermarked.jpg",
    watermark="logo.png",
    position="bottom-right",
    opacity=0.5,
)
```

### Sprite sheets

```python
from pixopt.sprite import create_sprite

result = create_sprite(
    ["icon1.png", "icon2.png", "icon3.png"],
    "sprite.png",
    layout="grid",
    fmt="PNG",
)
```

### Asset bundles

```python
from pixopt.bundle import generate_asset_bundle

bundle = generate_asset_bundle("photo.jpg", "./bundle")
print(bundle.dominant_color)
```

### PDF export

```python
from pixopt.pdf_io import images_to_pdf

pdf = images_to_pdf(
    ["page1.jpg", "page2.jpg"],
    "output.pdf",
)
```

### Next-gen formats

```python
from pixopt.nextgen import convert_to_nextgen

convert_to_nextgen("photo.jpg", "photo.jxl", fmt="jxl")
```

### Base64 and bytes I/O

```python
import base64
from pixopt import optimize_base64, base64_to_image

with open("photo.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("ascii")

result = optimize_base64(b64, output_format="WEBP", quality=80)
print(result.base64)  # optimized base64 string
```

---

## API Reference

For the complete auto-generated API documentation, visit the [official docs](https://mathiaspaulenko.github.io/pixopt/api/).

Key modules:

- `pixopt.optimizer` — Core optimization functions (`optimize_image`, `optimize_directory`, `convert_to_favicon`)
- `pixopt.models` — Data models (`OptimizationResult`, `OutputFormat`)
- `pixopt.placeholder` — Placeholder generation (`generate_placeholder`, `extract_dominant_color`, `generate_lqip_datauri`, `generate_blurhash`)
- `pixopt.smart_format` — Smart format detection (`detect_optimal_format`)
- `pixopt.srcset_generator` — Responsive image generation (`generate_srcset_images`, `SrcsetImage`)
- `pixopt.adaptive_quality` — Adaptive quality (`find_quality_for_target_size`)
- `pixopt.html_comparison` — Visual comparison (`generate_comparison_html`)
- `pixopt.watermark` — Watermarking (`add_text_watermark`, `add_image_watermark`)
- `pixopt.sprite` — Sprite sheets and contact sheets (`create_sprite`, `create_contact_sheet`)
- `pixopt.bundle` — Asset bundles (`generate_asset_bundle`)
- `pixopt.pdf_io` — PDF import/export (`images_to_pdf`, `pdf_to_images`)
- `pixopt.nextgen` — Next-gen formats (`convert_to_nextgen`)
- `pixopt.perceptual` — Duplicate detection (`find_duplicates`, `compute_hash`, `scan_duplicates`)
- `pixopt.inventory` — Directory scanning and reporting (`scan_directory`, `ScanReport`)
- `pixopt.benchmark` — Format benchmarking (`benchmark_formats`)
- `pixopt.palette` — Color palette extraction (`extract_palette`)
- `pixopt.io_bytes` — Base64 and bytes I/O (`optimize_base64`, `base64_to_image`)
- `pixopt.async_api` — Async operations (`async_optimize_image`, `async_batch_optimize`)
- `pixopt.pipeline` — Fluent optimization pipeline (`Pipeline`)
- `pixopt.presets` — Built-in and custom presets (`BUILTIN_PRESETS`, `apply_preset`)

---

## Development

Install in development mode:

```bash
git clone https://github.com/MathiasPaulenko/pixopt.git
cd pixopt
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run tests:

```bash
pytest tests/ -v
```

Run linters, type checkers, format check, and security checks:

```bash
ruff check .
ruff format . --check
mypy pixopt
python -m pyright
python -m bandit -r pixopt
python -m pip_audit .
```

Build documentation locally:

```bash
pip install -e ".[docs]"
mkdocs serve
```

---

## Contributing

We welcome contributions! Please read our [Contributing Guide](https://github.com/MathiasPaulenko/pixopt/blob/main/CONTRIBUTING.md) for details on code style, testing, and the pull request workflow.

Quick setup:

```bash
git clone https://github.com/MathiasPaulenko/pixopt.git
cd pixopt
pip install -e ".[dev]"
pytest
```

---

## Changelog

See [CHANGELOG.md](https://github.com/MathiasPaulenko/pixopt/blob/main/CHANGELOG.md) for the full history of changes.

---

## Acknowledgements

pixopt is built on top of the excellent Python imaging and CLI ecosystem, especially [Pillow](https://python-pillow.org/), [pillow-heif](https://github.com/bigcat88/pillow_heif), [Typer](https://typer.tiangolo.com/), [Rich](https://github.com/Textualize/rich), [piexif](https://github.com/hMatoba/piexif), and [NumPy](https://numpy.org/).

---

## License

[MIT License](https://github.com/MathiasPaulenko/pixopt/blob/main/LICENSE) — © 2026 pixopt contributors
