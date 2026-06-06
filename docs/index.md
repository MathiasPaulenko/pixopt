---
hide:
  - navigation
  - toc
---

# ImgOptimizer

A powerful, easy-to-use Python library and CLI tool for optimizing images for web and storage.

## Features

- **Size reduction** — resize images to maximum width/height while keeping aspect ratio
- **Format conversion** — convert between JPEG, PNG, WEBP, AVIF, GIF, HEIC/HEIF and SVG
- **Animated GIF → WEBP** – convert animated GIFs to much lighter animated WEBP
- **SVG minification** — pure-Python SVG cleanup (no Node.js tools needed)
- **HEIC/HEIF import** — open iPhone photos directly thanks to `pillow-heif`
- **Lossless mode** — lossless PNG/WEBP compression for UI assets that need pixel-perfect fidelity
- **Adaptive quality** — binary-search quality to hit a target file size automatically
- **Visual comparison** — generate interactive HTML before/after sliders
- **Responsive srcset** — generate multiple width variants and HTML `<img srcset="...">` snippets
- **Lazy-loading placeholders** — extract dominant color, generate LQIP data URIs, or blurhash strings
- **Smart format detection** — auto-detect the most efficient format (photo → WEBP, graphic → PNG, transparent → WEBP)
- **Backup originals** — copy originals to a backup directory before processing
- **Min-size filter** — skip files already below a size threshold
- **Metadata stripping** — remove EXIF and other metadata to save space
- **Quality tuning** — adjustable compression quality (1-100)
- **Progressive JPEG** — enable progressive encoding for better web delivery
- **Batch processing** — optimize single files, directories, or multiple files at once
- **CLI with Typer** — intuitive command-line interface with beautiful output

## Quick start

=== "CLI"

    ```bash
    pip install imgoptimizer
    imgoptimizer optimize photo.jpg --quality 80 --width 1200
    ```

=== "Library"

    ```python
    from imgoptimizer import optimize_image
    from imgoptimizer.models import OutputFormat

    result = optimize_image(
        "photo.jpg",
        "photo_optimized.webp",
        max_width=1200,
        quality=80,
        output_format=OutputFormat.WEBP,
    )
    print(f"Saved {result.savings_percent:.1f}%")
    ```

## License

MIT
