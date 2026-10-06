# Advanced Usage

This guide covers the advanced `pixopt` APIs. It assumes you are already comfortable with `optimize_image` and the basic CLI. Each section explains a feature, lists the key parameters and result objects, and provides runnable examples.

---

## Watermarking

`pixopt` can overlay text or a logo onto an image with configurable position, opacity, padding, and scaling. Use `WatermarkPosition` to place the mark in one of the corners or in the center.

### Text watermarks

```python
from pixopt import add_text_watermark, WatermarkPosition

result = add_text_watermark(
    "photo.jpg",
    "photo_watermarked.jpg",
    "© 2025 My Company",
    position=WatermarkPosition.BOTTOM_RIGHT,
    opacity=0.5,
    padding=20,
    font_size=48,
    font_path="fonts/Arial.ttf",  # optional; when omitted, arial.ttf or a default font is used
    color=(255, 255, 255),
)
print(result.output_path, result.width, result.height)
```

| Parameter | Default | Description |
| --- | --- | --- |
| `position` | `BOTTOM_RIGHT` | One of `TOP_LEFT`, `TOP_RIGHT`, `BOTTOM_LEFT`, `BOTTOM_RIGHT`, `CENTER` |
| `opacity` | `0.5` | Opacity from `0.0` (invisible) to `1.0` (opaque) |
| `padding` | `20` | Pixel distance from the edge |
| `font_size` | `36` | Text size in pixels |
| `font_path` | `None` | Path to a `.ttf` or `.otf` font file |
| `color` | `(255, 255, 255)` | Text color as an `(R, G, B)` tuple |

### Image watermarks

```python
from pixopt import add_image_watermark, WatermarkPosition

result = add_image_watermark(
    "photo.jpg",
    "photo_branded.jpg",
    "logo.png",
    position=WatermarkPosition.BOTTOM_LEFT,
    opacity=0.6,
    padding=30,
    scale=0.15,  # watermark width is 15% of the base image width
)
print(result.output_path, result.width, result.height)
```

!!! tip
    Use a PNG with an alpha channel for image watermarks. The watermark is composited with alpha, so a transparent logo blends cleanly onto the base image.

!!! warning
    `add_text_watermark` rejects text longer than 1000 characters, and both watermark functions enforce the package-wide maximum image dimension of 30,000 pixels.

---

## Sprite Sheets and Contact Sheets

Combine many images into a single file for game assets, CSS sprites, or thumbnail indexes.

### Sprite sheets

```python
from pathlib import Path
from pixopt import create_sprite, SpriteLayout

frames = sorted(Path("frames").glob("*.png"))
result = create_sprite(
    frames,
    "sprite_sheet.png",
    cell_width=128,
    cell_height=128,
    columns=4,
    layout=SpriteLayout.GRID,
    padding=2,
    background=(255, 255, 255),
    fmt="PNG",
)
print(f"Sprite: {result.width}x{result.height}, {result.rows}x{result.columns}")
for slot in result.slots:
    print(slot.index, slot.x, slot.y, slot.width, slot.height)
```

### Contact sheets

```python
from pixopt import create_contact_sheet

photos = ["img_01.jpg", "img_02.jpg", "img_03.jpg"]
result = create_contact_sheet(
    photos,
    "contact_sheet.jpg",
    cell_width=200,
    cell_height=200,
    columns=3,
    padding=10,
    label_height=20,
    fmt="JPEG",
)
```

`create_contact_sheet` adds the filename under each thumbnail and draws a thin border around every cell.

| Layout | Description |
| --- | --- |
| `GRID` | Square-ish grid with auto-calculated row and column counts |
| `HORIZONTAL` | One row, every image side-by-side |
| `VERTICAL` | One column, every image stacked |

!!! note
    `create_sprite` defaults `cell_width` and `cell_height` to the largest source image size, so each image fits without being enlarged unless you request it. Both functions are limited to 200 source images and 1 billion source pixels.

---

## Asset Bundles

`generate_asset_bundle` produces a complete set of web assets from a single source image: hero, thumbnail, `og:image`, favicon, srcset variants, LQIP data URI, blurhash, dominant color, and color palette.

```python
from pixopt import generate_asset_bundle, BundleOptions

options = BundleOptions(
    hero_width=1920,
    thumbnail_width=300,
    og_width=1200,
    og_height=630,
    favicon_sizes=[16, 32, 48, 64, 128, 256],
    srcset_widths=[320, 640, 960, 1280, 1920],
    quality=85,
    lqip_size=32,
    lqip_quality=20,
    palette_n=6,
)

bundle = generate_asset_bundle("hero.jpg", "assets/", options=options)

print(bundle.hero)
print(bundle.thumbnail)
print(bundle.og_image)
print(bundle.favicon)
print(bundle.srcset_images)
print(bundle.lqip_data_uri)
print(bundle.blurhash)
print(bundle.dominant_color)
print(bundle.palette)
```

| `BundleOptions` field | Default | Description |
| --- | --- | --- |
| `hero_width` | `1920` | Hero image width |
| `thumbnail_width` | `300` | Thumbnail width |
| `og_width` / `og_height` | `1200` / `630` | Open Graph image size, cropped with `fit="cover"` |
| `favicon_sizes` | `[16, 32, 48, 64, 128, 256]` | ICO resolutions to generate |
| `srcset_widths` | `[320, 640, 960, 1280, 1920]` | Responsive width variants |
| `palette_n` | `6` | Number of dominant colors to extract (1-32) |
| `quality` | `85` | Quality for generated images |
| `lqip_size` / `lqip_quality` | `32` / `20` | Low-quality image placeholder size and quality |
| `generate_*` flags | `True` | Toggle each output type individually |

---

## PDF Import and Export

Convert PDF pages to images and images to PDF. PDF support is optional and requires `PyMuPDF`.

```bash
pip install pixopt[pdf]
```

### Import PDF to images

```python
from pixopt import pdf_to_images

result = pdf_to_images(
    "document.pdf",
    "pdf_pages/",
    dpi=150,
    fmt="PNG",
    prefix="doc",
)
print(result.total_pages)
for page in result.pages:
    print(page.page_number, page.width, page.height, page.output_path)
```

### Export images to PDF

```python
from pixopt import images_to_pdf

result = images_to_pdf(
    ["page_1.png", "page_2.png", "page_3.png"],
    "output.pdf",
    title="My Document",
)
print(result.output, result.page_count)
```

!!! warning
    `pdf_to_images` returns a `PdfImportResult` with `success=False` if `PyMuPDF` is not installed, the PDF exceeds 50 MB, or it has more than 100 pages. Page images are named `{prefix}_{page:04d}.{fmt}`.

---

## Next-Generation Formats (JXL / WebP 2)

`pixopt` can detect and convert to next-generation formats when Pillow or a compatible plugin supports them.

```python
from pixopt import (
    detect_format_support,
    is_format_supported,
    convert_to_nextgen,
    NextGenFormat,
)

support = detect_format_support()
for info in support.formats:
    print(info.format, info.supported, info.note)

if is_format_supported(NextGenFormat.JXL):
    result = convert_to_nextgen(
        "photo.jpg",
        "photo.jxl",
        fmt=NextGenFormat.JXL,
        quality=85,
        fallback=True,
        fallback_format="WEBP",
    )
    print(result.output, result.supported, result.fallback, result.savings_percent)
```

| `NextGenFormat` | Description |
| --- | --- |
| `JXL` | JPEG XL. Requires `pillow-jxl-plugin` or native Pillow support. |
| `WEBP2` | WebP 2. Currently rarely supported by Pillow. |

`convert_to_nextgen` returns a `ConversionResult`. If the target format is not supported and `fallback=True`, it writes a `fallback_format` file and adjusts the output path extension.

!!! note
    Next-gen support is intentionally graceful. `detect_format_support` actually tries to encode a small test image, so the result reflects the real capabilities of the installed environment.

---

## Duplicate Detection

Find duplicate or near-duplicate images using perceptual hashing. The scan supports `phash`, `dhash`, and `ahash`.

```python
from pixopt import scan_duplicates, compute_hash, hamming_distance

report = scan_duplicates(
    "./gallery",
    algorithm="phash",
    threshold=5,
    recursive=True,
    hash_size=8,
)
print(report.total_files, report.total_duplicates)
for group in report.duplicate_groups:
    print(group.hash_hex, group.count, group.files)
```

Compare two images directly:

```python
h1 = compute_hash("image_a.jpg", algorithm="phash", hash_size=8)
h2 = compute_hash("image_b.jpg", algorithm="phash", hash_size=8)
distance = hamming_distance(h1.hash_hex, h2.hash_hex)
print(f"Hamming distance: {distance}")
```

| Parameter | Description |
| --- | --- |
| `algorithm` | `phash`, `dhash`, or `ahash` |
| `threshold` | Maximum Hamming distance to consider images duplicates. `0` means exact matches only. |
| `hash_size` | Side length in bits; `8` produces a 64-bit hash |

!!! tip
    Use `threshold=0` for fast exact-duplicate grouping. Use a small positive threshold such as `5` for near-duplicate detection.

---

## Directory Scanning and Inventory

`scan_directory` inventories a folder and returns structured metadata plus aggregate statistics.

```python
from pixopt import scan_directory

report = scan_directory(
    "./images",
    recursive=True,
    extensions=[".jpg", ".png", ".webp"],
)

print(report.total_files)
print(report.valid_images)
print(report.errors)
print(report.human_total_size)
print(report.formats)

for entry in report.entries:
    print(entry.file_path, entry.format, entry.width, entry.height, entry.human_file_size)
```

`ScanEntry` contains `file_path`, `file_size`, `width`, `height`, `format`, `mode`, `has_alpha`, `is_animated`, `frame_count`, and `error` (if the file could not be read). `ScanReport` adds totals, a format histogram, and the largest and smallest files.

!!! note
    The scan stops at 10,000 entries (`MAX_SCAN_ENTRIES`) to prevent runaway processing. Use `extensions` to limit the file types and `recursive=True` to descend into subdirectories.

---

## Format Benchmarking

`benchmark_formats` encodes an image in several formats and quality levels, then recommends the smallest variant.

```python
from pixopt import benchmark_formats

result = benchmark_formats(
    "photo.jpg",
    qualities=[50, 60, 70, 80, 90],
    formats=["JPEG", "WEBP", "AVIF", "PNG"],
)

for variant in result.variants:
    print(variant.format, variant.quality, variant.size_bytes, f"{variant.savings_percent}%")

print("Recommended:", result.recommended_format, result.recommended_quality)
print("Savings:", result.recommended_savings)
```

| Result field | Description |
| --- | --- |
| `source_size` | Original file size in bytes |
| `variants` | List of `BenchmarkVariant` results |
| `recommended_format` | Smallest successful format |
| `recommended_quality` | Quality setting for the recommendation, or `None` for PNG |
| `recommended_size` / `recommended_savings` | Size and savings of the recommendation |

!!! note
    PNG is lossless and is benchmarked once with no quality parameter. AVIF is automatically skipped if the environment cannot encode it.

---

## Color Palette Extraction

Extract dominant colors from an image for design systems or theme generation.

```python
from pixopt import extract_palette

palette = extract_palette("photo.jpg", n=6)
print(palette.width, palette.height)
for swatch in palette.colors:
    print(swatch.hex, swatch.rgb, f"{swatch.percent}%")
```

`extract_palette` uses Pillow's median-cut quantization. It returns a `PaletteResult` with a list of `ColorSwatch` objects sorted by dominance. `n` must be between 1 and 32.

---

## Base64 / Bytes Workflows

The `io_bytes` module lets you optimize images that live only in memory. This is useful for web backends, APIs, and the `pixopt` MCP server.

### Optimize raw bytes

```python
from pixopt import optimize_bytes
from pixopt.models import OutputFormat

with open("photo.jpg", "rb") as f:
    data = f.read()

result = optimize_bytes(
    data,
    max_width=1200,
    quality=80,
    output_format=OutputFormat.WEBP,
)
print(result.format, result.width, result.height)
print(result.original_size, result.optimized_size, result.savings_percent)

# Write the optimized bytes back to disk
with open("photo_optimized.webp", "wb") as f:
    f.write(result.data)
```

### Optimize a base64 string

```python
from pixopt import optimize_base64, OutputFormat

b64 = "..."  # raw base64, without the data URI prefix
result = optimize_base64(
    b64,
    max_width=800,
    quality=75,
    output_format=OutputFormat.WEBP,
)
print(result.base64[:80], result.optimized_size)
```

### Convert between PIL, bytes, and base64

```python
from PIL import Image
from pixopt import (
    bytes_to_image,
    image_to_bytes,
    image_to_base64,
    base64_to_image,
)

img = Image.open("photo.png")
encoded = image_to_base64(img, fmt="WEBP", quality=85)
img.close()

decoded = base64_to_image(encoded)
print(decoded.size)
decoded.close()
```

!!! warning
    `bytes_to_image` and `base64_to_image` return a loaded `PIL.Image.Image`. The caller is responsible for calling `.close()`. Input bytes are capped at 100 MB; base64 strings are capped at 1 MB.

---

## Async API

All CPU-bound work is dispatched to a background thread with `asyncio.to_thread`, so the event loop stays responsive. The main entry points are `async_optimize_image`, `async_batch_optimize`, and `async_optimize_base64`.

```python
import asyncio
from pixopt import (
    async_optimize_image,
    async_batch_optimize,
    async_optimize_base64,
)
from pixopt.models import OutputFormat


async def main():
    single = await async_optimize_image(
        "photo.jpg",
        "photo.webp",
        max_width=1200,
        quality=80,
        output_format=OutputFormat.WEBP,
    )
    print(single.savings_percent)

    report = await async_batch_optimize(
        ["a.jpg", "b.jpg", "c.png"],
        "optimized/",
        max_width=1200,
        quality=80,
        output_format=OutputFormat.WEBP,
        max_concurrency=4,
    )
    print(report.total_files, report.succeeded, report.failed)
    print(report.total_savings_percent)

    b64_result = await async_optimize_base64(b64_input, max_width=800)
    print(b64_result.optimized_size)


asyncio.run(main())
```

### Progress callbacks

`async_batch_optimize` accepts an `on_progress` callback that receives a `ProgressInfo` object:

```python
from pixopt import async_batch_optimize
from pixopt.progress import ProgressInfo


def on_progress(info: ProgressInfo) -> None:
    print(f"{info.current}/{info.total} {info.current_file.name}")


await async_batch_optimize(
    ["a.jpg", "b.jpg"],
    "out/",
    max_width=1200,
    on_progress=on_progress,
)
```

!!! tip
    Adjust `max_concurrency` based on your workload. The default is 4; raising it helps for many small files, while lowering it reduces memory pressure on large images.

---

## Perceptual Hashing

Compute pHash, dHash, or aHash for an image and compare hashes with Hamming distance.

```python
from pixopt import compute_hash, hamming_distance, phash, dhash, ahash

# Direct algorithms
print(ahash("photo.jpg", hash_size=8))
print(dhash("photo.jpg", hash_size=8))
print(phash("photo.jpg", hash_size=8, highfreq_factor=4))

# Generic wrapper
h1 = compute_hash("photo.jpg", algorithm="phash", hash_size=8)
h2 = compute_hash("photo_copy.jpg", algorithm="phash", hash_size=8)

print(h1.hash_hex, h2.hash_hex)
print(hamming_distance(h1.hash_hex, h2.hash_hex))
```

| Algorithm | Best for |
| --- | --- |
| `ahash` | Fast, brightness-tolerant comparison |
| `dhash` | Detecting small changes and crops |
| `phash` | Robust to resizing and compression |

`compute_hash` returns a `HashResult` with `file_path`, `algorithm`, `hash_hex`, and `hash_size`.

---

## Quality Metrics and `compare_images`

Compare an original image against an optimized or modified version with SSIM, PSNR, and MSE.

```python
from pixopt import compare_images, compute_ssim, compute_psnr
import numpy as np
from PIL import Image

# High-level comparison
metrics = compare_images("original.jpg", "optimized.webp")
print(f"SSIM: {metrics.ssim}")
print(f"PSNR: {metrics.psnr}")
print(f"MSE: {metrics.mse}")
print(f"Verdict: {metrics.verdict}")
```

For lower-level control, work with numpy arrays directly:

```python
arr1 = np.asarray(Image.open("original.jpg").convert("RGB"), dtype=np.float32)
arr2 = np.asarray(Image.open("optimized.webp").convert("RGB"), dtype=np.float32)

ssim = compute_ssim(arr1, arr2, win_size=7, data_range=255.0)
mse = np.mean((arr1 - arr2) ** 2)
psnr = compute_psnr(mse)
print(ssim, psnr)
```

| `QualityMetrics` field | Description |
| --- | --- |
| `ssim` | Structural similarity in `[-1, 1]`; `1.0` is identical |
| `psnr` | Peak signal-to-noise ratio, or `None` when MSE is `0` |
| `mse` | Mean squared error |
| `verdict` | `excellent`, `good`, `fair`, or `poor` based on SSIM |

!!! warning
    `compare_images` requires both images to have the same dimensions. SSIM computation is limited to 4 megapixels (`MAX_SSIM_PIXELS`).

---

## Presets

Presets bundle common optimization settings. Built-in presets include `web`, `social`, `thumbnail`, `e-commerce`, and `print`.

```python
from pixopt import (
    BUILTIN_PRESETS,
    get_preset_names,
    resolve_preset,
    apply_preset,
    load_custom_presets,
)

print(get_preset_names())
print(BUILTIN_PRESETS["web"])

# Resolve to a flat dict
web = resolve_preset("web")
print(web)

# Merge with overrides (keys use the dashed preset naming)
merged = apply_preset("web", **{"max-width": 1200, "quality": 90})
print(merged)

# Load custom presets from JSON
custom = load_custom_presets("my_presets.json")
combined = apply_preset("my-preset", custom_presets=custom)
```

Example `my_presets.json`:

```json
{
  "my-preset": {
    "quality": 92,
    "strip": false,
    "fit": "contain",
    "max-width": 1600,
    "background-color": "#ffffff"
  }
}
```

!!! note
    Preset keys are CLI-style dashed names such as `max-width`, `aspect-ratio`, and `background-color`. If you want to pass a preset directly to `optimize_image`, convert the keys to the snake_case names that the Python API uses, or pass the values explicitly.

---

## The `Pipeline` Fluent API

`Pipeline` lets you chain image operations and run them in a single call. Each method returns `self`, so calls can be chained.

```python
from pixopt import Pipeline, OutputFormat, WatermarkPosition

pipeline = (
    Pipeline()
    .open("photo.jpg")
    .auto_orient()
    .resize(max_width=1200, fit="cover")
    .watermark_text(
        "© 2025",
        position=WatermarkPosition.BOTTOM_RIGHT,
        opacity=0.5,
        font_size=48,
    )
    .optimize(quality=85, output_format=OutputFormat.WEBP)
    .save("output/photo.webp")
)

result = pipeline.run()
print(result.output_path)
print(result.width, result.height, result.format, result.size_bytes)
print(result.steps_executed)

# Inspect the queued steps without running them
print(pipeline.steps)
```

### Image watermark in a pipeline

```python
pipeline = (
    Pipeline()
    .open("photo.jpg")
    .resize(max_width=1200)
    .watermark_image(
        "logo.png",
        position=WatermarkPosition.BOTTOM_LEFT,
        opacity=0.6,
        scale=0.12,
    )
    .optimize(quality=85, output_format=OutputFormat.WEBP)
    .save("output/photo.webp")
)
result = pipeline.run()
```

| Method | Purpose |
| --- | --- |
| `.open(path)` | Set the source image |
| `.auto_orient()` | Apply EXIF orientation |
| `.resize(...)` | Resize with `fit`, `anchor`, `aspect_ratio`, and `background_color` |
| `.convert(mode)` | Convert color mode, e.g. `"RGB"`, `"RGBA"`, `"L"` |
| `.watermark_text(...)` | Add a text watermark |
| `.watermark_image(...)` | Add an image watermark |
| `.optimize(...)` | Configure quality, format, progressive, optimize, lossless, strip |
| `.save(path)` | Set the output path |
| `.run()` | Execute the pipeline and return a `PipelineResult` |

!!! tip
    The pipeline automatically creates intermediate temporary files for watermark operations, so you can chain resize and watermark steps without manual file management.
