# pixopt

<p style="text-align: center;">
  <em>A powerful, easy-to-use Python library and CLI tool for optimizing images for web and storage.</em>
</p>

<p style="text-align: center;">
  <a href="https://pypi.org/project/pixopt/">![PyPI](https://img.shields.io/pypi/v/pixopt)</a>
  <a href="https://pypi.org/project/pixopt/">![Python](https://img.shields.io/pypi/pyversions/pixopt)</a>
  <a href="https://github.com/MathiasPaulenko/pixopt/actions/workflows/ci.yml">![CI](https://img.shields.io/github/actions/workflow/status/MathiasPaulenko/pixopt/ci.yml?label=CI)</a>
  <a href="https://github.com/MathiasPaulenko/pixopt/blob/main/LICENSE">![License](https://img.shields.io/github/license/MathiasPaulenko/pixopt)</a>
</p>

---

## What is pixopt?

**pixopt** is a fast Python image optimizer designed for modern web workflows. It provides both a rich **command-line interface (CLI)** and a clean **Python API** to resize, compress, convert formats, generate responsive assets, extract lazy-loading placeholders, and detect the optimal format automatically.

Whether you are a developer automating image pipelines, a designer preparing assets, or a DevOps engineer optimizing static sites, pixopt handles the heavy lifting so you don't have to.

---

## Highlights

- **Format conversion** — JPEG, PNG, WEBP, AVIF, GIF, HEIC/HEIF, SVG
- **Animated GIF to WEBP** — convert animated GIFs to much lighter animated WEBP
- **SVG minification** — pure-Python SVG cleanup (no Node.js tools needed)
- **HEIC/HEIF import** — open iPhone photos directly via `pillow-heif`
- **Lossless compression** — lossless PNG/WEBP for UI assets
- **Adaptive quality** — binary-search quality to hit a target file size
- **Smart format detection** — auto-select WEBP/JPEG/PNG based on content
- **Responsive srcset** — generate multiple width variants + HTML snippets
- **Lazy-loading placeholders** — dominant color, LQIP data URI, blurhash
- **Visual comparison** — interactive HTML before/after slider
- **Watermarking** — add text or image watermarks with opacity and positioning
- **Sprite and contact sheets** — combine images into grids or thumbnail indexes
- **Asset bundles** — hero, thumbnail, `og:image`, favicon, srcset, LQIP, blurhash, and palette in one call
- **PDF import and export** — convert PDF pages to images and images to PDF
- **Next-generation formats** — JXL and WebP 2 conversion with graceful fallback
- **Duplicate detection** — find duplicate or near-duplicate images with perceptual hashing
- **Directory scanning** — inventory images with aggregate statistics
- **Format benchmarking** — compare JPEG/WEBP/AVIF/PNG variants and get a recommendation
- **Color palette extraction** — extract dominant colors for themes and design systems
- **Bytes and base64 workflows** — optimize in-memory images for web backends and APIs
- **Async API** — non-blocking optimization, batch, and base64 processing
- **Quality metrics** — SSIM, PSNR, and MSE comparison
- **Perceptual hashing** — pHash, dHash, aHash with Hamming distance
- **Presets** — built-in and custom optimization profiles
- **Pipeline API** — chain operations with a fluent interface
- **Batch processing** — single files, directories, or multiple files at once
- **Backup originals** — copy originals before processing
- **Beautiful CLI** — built with Typer for an intuitive experience

---

## Quick Start

=== "CLI"

    Install and run in one line:

    ```bash
    pip install pixopt
    pixopt optimize photo.jpg photo_optimized.jpg --quality 80 --width 1200
    ```

=== "Library"

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

## Next Steps

- [:material-rocket-launch: Installation](installation.md) — Install pixopt on your system
- [:material-console: CLI Usage](cli.md) — Learn every CLI command with examples
- [:material-code-braces: Library Usage](library.md) — Use pixopt programmatically in Python
- [:material-book-open: Advanced Usage](advanced.md) — Watermarking, sprites, bundles, PDFs, async, presets, and more
- [:material-api: API Reference](api.md) — Browse the full auto-generated API docs
- [:material-source-branch: Contributing](contributing.md) — Set up your dev environment and contribute

---

## License

MIT License — see [LICENSE](https://github.com/MathiasPaulenko/pixopt/blob/main/LICENSE) for details.
