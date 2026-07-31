# Library Usage

`pixopt` is a Python library as well as a CLI. Every CLI feature is exposed through a typed, public Python API under the `pixopt` package, so you can build custom pipelines, web backends, automation scripts, and MCP integrations.

All examples below use the exact import and parameter names exported by `pixopt`. You can import most helpers directly from the top-level package:

```python
import pixopt
from pixopt import (
    optimize_image,
    optimize_directory,
    batch_optimize,
    OutputFormat,
    FitMode,
    Anchor,
    PlaceholderType,
    WatermarkPosition,
    SpriteLayout,
    NextGenFormat,
    EXIFGroup,
)
```

!!! note
    Functions are typed with `pathlib.Path` support. You can pass strings or `Path` objects for all file paths.

---

## Common types

| Enum | Values | Notes |
|------|--------|-------|
| `OutputFormat` | `AUTO`, `JPEG`, `PNG`, `WEBP`, `AVIF`, `ORIGINAL` | `AUTO` infers from the output path or source. `ORIGINAL` keeps the source format. |
| `FitMode` | `down`, `cover`, `contain`, `fill` | How the image is resized within `max_width` / `max_height`. |
| `Anchor` | `center`, `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right`, `face` | Anchor point for `cover` / `contain` cropping. |
| `WatermarkPosition` | `top-left`, `top-right`, `bottom-left`, `bottom-right`, `center` | Position of text or image watermarks. |
| `SpriteLayout` | `grid`, `horizontal`, `vertical` | Layout strategy for sprite sheets. |
| `NextGenFormat` | `JXL`, `WEBP2` | Next-generation output formats. |
| `PlaceholderType` | `color`, `lqip`, `blurhash` | Placeholder generation modes. |

---

## Basic optimization

`optimize_image()` is the core single-image API. It handles resizing, format conversion, quality, metadata stripping, EXIF filtering, and backups in one call.

```python
from pixopt import optimize_image, OutputFormat

result = optimize_image(
    "photo.jpg",
    "photo_optimized.webp",
    max_width=1600,
    quality=85,
    strip_metadata=True,
    output_format=OutputFormat.WEBP,
)

print(f"Saved {result.savings_percent:.1f}%")
print(f"Output: {result.output_path}")
print(f"Original: {result.human_original_size}")
print(f"Optimized: {result.human_optimized_size}")
print(f"Dimensions: {result.width}x{result.height}")
```

!!! tip "Result object"
    `OptimizationResult` provides `source_path`, `output_path`, `original_size`, `optimized_size`, `savings_bytes`, `savings_percent`, `width`, `height`, `format`, `metadata_removed`, `success`, and `error`.

### Selective EXIF preservation

By default `strip_metadata=True` removes all EXIF. You can keep specific groups with `keep_exif_groups`:

```python
from pixopt import optimize_image, EXIFGroup

result = optimize_image(
    "photo.jpg",
    "photo_optimized.jpg",
    max_width=1600,
    quality=85,
    strip_metadata=True,
    keep_exif_groups={EXIFGroup.ORIENTATION, EXIFGroup.CAMERA, EXIFGroup.DATE},
)
```

!!! warning
    `keep_exif_groups` only takes effect when `strip_metadata=True`. It uses the `piexif` groups defined in `pixopt.exif.EXIFGroup`.

### Cropping and fit modes

```python
from pixopt import optimize_image, OutputFormat, FitMode, Anchor

# 16:9 cover crop centered on the image
result = optimize_image(
    "photo.jpg",
    "banner.webp",
    max_width=1920,
    max_height=1080,
    aspect_ratio=(16, 9),
    fit=FitMode.COVER,
    anchor=Anchor.CENTER,
    output_format=OutputFormat.WEBP,
    quality=80,
)
```

---

## Batch and directory processing

### Directory optimization

`optimize_directory()` scans a directory and returns a list of `OptimizationResult` objects.

```python
from pixopt import optimize_directory, OutputFormat

def progress(info):
    print(f"{info.current}/{info.total}: {info.current_file.name} -> {info.success}")

results = optimize_directory(
    "./images",
    "./optimized",
    recursive=True,
    extensions={".jpg", ".jpeg", ".png"},
    max_width=1200,
    quality=80,
    output_format=OutputFormat.WEBP,
    backup_dir="./backups",
    min_size_bytes=1024,
    on_progress=progress,
)

successful = [r for r in results if r.success]
print(f"Processed {len(successful)}/{len(results)} files")
```

!!! note
    `output_dir=None` overwrites images in-place. You must set `overwrite=True` explicitly when you want `optimize_image()` to overwrite the source.

### Batch optimization from a list

`batch_optimize()` accepts an iterable of paths and writes all outputs into a single directory. It returns a `BatchReport`.

```python
from pathlib import Path
from pixopt import batch_optimize, OutputFormat

paths = [Path("a.jpg"), Path("b.png"), Path("c.webp")]
report = batch_optimize(
    paths,
    "./optimized",
    max_width=800,
    quality=80,
    output_format=OutputFormat.WEBP,
)

print(report.to_dict())
print(f"Total: {report.total_files}")
print(f"Succeeded: {report.succeeded}, Failed: {report.failed}")
print(f"Savings: {report.human_total_savings} ({report.total_savings_percent:.1f}%)")
```

!!! tip
    `batch_optimize` is ideal when you already have a list of files. `optimize_directory` is ideal when you want to discover files on disk.

---

## Format conversion

Convert to a different format without resizing or quality changes. The simplest approach is `optimize_image()` with `output_format`:

```python
from pixopt import optimize_image, OutputFormat

result = optimize_image(
    "icon.png",
    "icon.webp",
    output_format=OutputFormat.WEBP,
    lossless=True,
)
```

You can also use the convenience wrapper `change_extension()`:

```python
from pixopt import change_extension, OutputFormat

result = change_extension(
    "photo.png",
    "photo.avif",
    output_format=OutputFormat.AVIF,
    quality=80,
)
```

!!! note
    `change_extension()` forwards all other parameters to `optimize_image()`. If `output` is omitted, set `overwrite=True` to overwrite the source.

---

## Lossless compression

Use `lossless=True` for UI assets, icons, screenshots, and graphics where pixel-perfect fidelity is required:

```python
from pixopt import optimize_image, OutputFormat

# WEBP lossless
result = optimize_image(
    "ui_asset.png",
    "ui_asset.webp",
    output_format=OutputFormat.WEBP,
    lossless=True,
)

# PNG lossless (default PNG behavior)
result_png = optimize_image(
    "screenshot.png",
    "screenshot_optimized.png",
    output_format=OutputFormat.PNG,
)
```

!!! note
    `lossless` is only honored by PNG and WEBP. JPEG does not support lossless compression.

---

## Adaptive quality (target file size)

`find_quality_for_target_size()` performs a binary search in memory to find the JPEG/WEBP quality that lands closest to a target byte size.

```python
from PIL import Image
from pixopt import optimize_image, OutputFormat
from pixopt.adaptive_quality import find_quality_for_target_size

with Image.open("photo.jpg") as img:
    img.load()
    quality = find_quality_for_target_size(
        img,
        "JPEG",
        target_size=50 * 1024,
        min_quality=60,
        max_quality=95,
        tolerance=0.05,
        max_iterations=8,
    )

result = optimize_image(
    "photo.jpg",
    "photo_50kb.jpg",
    output_format=OutputFormat.JPEG,
    quality=quality,
)

print(f"Achieved quality: {quality}")
print(f"Final size: {result.human_optimized_size}")
```

!!! warning
    `target_size` is in **bytes**. The algorithm returns the highest quality that keeps the encoded file at or below the target size within the tolerance.

---

## Placeholders

Generate tiny placeholders for lazy-loading with `generate_placeholder()`:

```python
from pixopt.placeholder import generate_placeholder, PlaceholderType

# Dominant color as a CSS hex string
color = generate_placeholder("photo.jpg", placeholder_type=PlaceholderType.COLOR)
# -> "#3f7a8c"

# LQIP: tiny base64 blurred preview
lqip = generate_placeholder(
    "photo.jpg",
    placeholder_type=PlaceholderType.LQIP,
    lqip_size=32,
    lqip_quality=20,
)
# -> "data:image/jpeg;base64,/9j/4AAQ..."

# Blurhash-like compact string
blurhash = generate_placeholder("photo.jpg", placeholder_type=PlaceholderType.BLURHASH)
# -> "LEHV6nWB2yk8pyo0adR*.7kCMdnj"
```

!!! tip
    LQIP is ideal for immediate visual feedback while images load. Blurhash is ideal when your frontend already has a blurhash decoder.

---

## Smart format detection

`detect_optimal_format()` analyzes image content and recommends the most efficient output format.

```python
from pixopt.smart_format import detect_optimal_format, is_photo, has_transparency, count_unique_colors
from pixopt.models import OutputFormat

fmt = detect_optimal_format("photo.jpg")
# -> OutputFormat.WEBP for photographs

fmt = detect_optimal_format("icon.png")
# -> OutputFormat.WEBP or OutputFormat.PNG for graphics

fmt = detect_optimal_format(
    "logo_with_alpha.png",
    allow_lossless=True,
    allow_lossy=True,
)
```

You can also run the individual heuristics directly:

```python
from PIL import Image

with Image.open("photo.jpg") as img:
    print(f"Is photo: {is_photo(img)}")
    print(f"Has alpha: {has_transparency(img)}")
    print(f"Unique colors: {count_unique_colors(img)}")
```

| Content | Default recommendation |
|---------|------------------------|
| Photographs | `OutputFormat.WEBP` |
| Graphics / illustrations with few colors | `OutputFormat.WEBP` or `OutputFormat.PNG` |
| Transparent images | `OutputFormat.WEBP` (or `OutputFormat.PNG` if lossless only) |
| Animated images | `OutputFormat.WEBP` |

---

## Responsive srcset generation

`generate_srcset_images()` creates multiple resized variants for `srcset` attributes.

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
    print(f"{v.width}px -> {v.size_bytes} bytes ({v.output_path.name})")
```

This produces files like:

- `hero-320w.webp`
- `hero-640w.webp`
- `hero-1024w.webp`
- `hero-1920w.webp`

Use them in HTML:

```html
<img
  srcset="hero-320w.webp 320w,
          hero-640w.webp 640w,
          hero-1024w.webp 1024w,
          hero-1920w.webp 1920w"
  sizes="(max-width: 600px) 320px,
         (max-width: 1000px) 640px,
         1920px"
  src="hero-1920w.webp"
  alt="Hero image"
/>
```

!!! note
    Widths larger than the original image are skipped automatically. Results are sorted by width ascending.

---

## Backup and min-size filter

Protect originals and skip already-optimized files:

```python
from pixopt import optimize_image

result = optimize_image(
    "photo.jpg",
    "photo_optimized.jpg",
    quality=75,
    backup_dir="./backups",
    min_size_bytes=10240,
)

if not result.output_path.exists() and result.error:
    print(f"Skipped: {result.error}")
```

!!! warning
    When `min_size_bytes` is set and the source is already smaller, no output file is created. `result.success` is still `True` but `result.error` explains that the file was skipped.

---

## Favicon generation

`convert_to_favicon()` creates a multi-resolution `.ico` file.

```python
from pixopt import convert_to_favicon

result = convert_to_favicon(
    "logo.png",
    "favicon.ico",
    sizes=[16, 32, 48],
    background=(255, 255, 255),
    keep_transparency=True,
)

print(f"Favicon created: {result.output_path}")
```

!!! tip
    The default sizes when `sizes` is omitted are `[16, 32, 48, 64, 128, 256]`. The largest size determines the `width` and `height` reported in the result.

---

## Visual comparison

`generate_comparison_html()` builds a self-contained HTML page with an interactive before/after slider.

```python
from pixopt import generate_comparison_html

html_path = generate_comparison_html(
    before_path="photo.jpg",
    after_path="photo_optimized.jpg",
    output_html="comparison.html",
    title="Original vs. Optimized",
)

print(f"Comparison saved to: {html_path}")
```

!!! note
    The generated HTML embeds both images as base64 data URIs. Images over the internal base64 limit will raise an error; optimize them first if needed.

---

## Watermarking

### Text watermarks

```python
from pixopt import add_text_watermark, WatermarkPosition

result = add_text_watermark(
    "photo.jpg",
    "photo_watermarked.jpg",
    "(c) 2025 My Company",
    position=WatermarkPosition.BOTTOM_RIGHT,
    opacity=0.5,
    padding=20,
    font_size=48,
    color=(255, 255, 255),
)

print(f"Watermarked: {result.output_path} ({result.width}x{result.height})")
```

### Image watermarks

```python
from pixopt import add_image_watermark, WatermarkPosition

result = add_image_watermark(
    "photo.jpg",
    "photo_logo.jpg",
    "logo.png",
    position=WatermarkPosition.BOTTOM_RIGHT,
    opacity=0.5,
    padding=20,
    scale=0.2,
)
```

!!! tip
    For image watermarks, use a PNG with an alpha channel for the best results. `scale` is relative to the base image width.

---

## Sprite sheets

### Sprite sheet

`create_sprite()` combines multiple images into a single sheet.

```python
from pixopt import create_sprite, SpriteLayout

result = create_sprite(
    images=["icon1.png", "icon2.png", "icon3.png"],
    output="sprites.png",
    cell_width=64,
    cell_height=64,
    columns=3,
    layout=SpriteLayout.GRID,
    padding=2,
    fmt="PNG",
)

print(f"Sprite: {result.output}")
print(f"Dimensions: {result.width}x{result.height}")
print(f"Slots: {len(result.slots)}")
```

### Contact sheet

`create_contact_sheet()` generates a grid of thumbnails with filename labels.

```python
from pixopt import create_contact_sheet

result = create_contact_sheet(
    images=["a.jpg", "b.jpg", "c.jpg"],
    output="contact_sheet.png",
    cell_width=200,
    cell_height=200,
    padding=10,
    label_height=20,
    fmt="PNG",
)
```

!!! note
    `SpriteResult` includes `slots` with `index`, `source`, `x`, `y`, `width`, and `height` for each placed image.

---

## Asset bundles

`generate_asset_bundle()` generates a complete set of web assets from one source image in a single call.

```python
from pixopt import generate_asset_bundle, BundleOptions

options = BundleOptions(
    hero_width=1920,
    thumbnail_width=300,
    og_width=1200,
    og_height=630,
    favicon_sizes=[16, 32, 48, 128, 256],
    srcset_widths=[320, 640, 960, 1280, 1920],
    palette_n=6,
    quality=85,
    lqip_size=32,
    lqip_quality=20,
    generate_hero=True,
    generate_thumbnail=True,
    generate_og=True,
    generate_favicon=True,
    generate_srcset=True,
    generate_lqip=True,
    generate_blurhash=True,
    generate_palette=True,
    generate_dominant_color=True,
)

bundle = generate_asset_bundle(
    "hero.jpg",
    "./assets",
    options=options,
)

print(bundle.to_dict())
print(f"LQIP: {bundle.lqip_data_uri[:50]}...")
print(f"Dominant color: {bundle.dominant_color}")
print(f"Palette: {[c.hex for c in bundle.palette.colors]}")
```

!!! tip
    `AssetBundle` returns individual `OptimizationResult` objects for `hero`, `thumbnail`, `og_image`, and `favicon`, plus a list of `SrcsetImage` objects and placeholders.

---

## PDF export

`pixopt` can convert PDF pages to images and images to a PDF. PDF support requires the optional `PyMuPDF` dependency (`pip install pixopt[pdf]`).

### PDF to images

```python
from pixopt import pdf_to_images

result = pdf_to_images(
    "document.pdf",
    "./pdf_pages",
    dpi=150,
    fmt="PNG",
    prefix="page",
)

print(f"Pages: {result.total_pages}")
for page in result.pages:
    print(f"  {page.page_number}: {page.width}x{page.height} -> {page.output_path}")
```

### Images to PDF

```python
from pixopt import images_to_pdf

result = images_to_pdf(
    ["cover.jpg", "page1.jpg", "page2.jpg"],
    "output.pdf",
    title="My Document",
)

print(f"PDF written: {result.output} ({result.page_count} pages)")
```

!!! warning
    `pdf_to_images()` returns a `PdfImportResult` with `success=False` when `PyMuPDF` is not installed. `images_to_pdf()` uses Pillow and does not require `PyMuPDF`.

---

## Next-gen formats (JXL / WebP 2)

The `pixopt.nextgen` module supports JPEG XL and WebP 2 when the underlying Pillow plugins are available.

```python
from pixopt import (
    detect_format_support,
    is_format_supported,
    convert_to_nextgen,
    NextGenFormat,
)

# Check what is available
support = detect_format_support()
for info in support.formats:
    print(f"{info.format}: supported={info.supported}, note={info.note}")

# Convert to JXL, falling back to WEBP if not supported
result = convert_to_nextgen(
    "photo.jpg",
    "photo.jxl",
    fmt=NextGenFormat.JXL,
    quality=85,
    fallback=True,
    fallback_format="WEBP",
)

print(f"Format: {result.format}")
print(f"Fallback used: {result.fallback}")
print(f"Savings: {result.savings_percent:.1f}%")
```

!!! note
    `convert_to_nextgen()` gracefully falls back to `fallback_format` when the requested next-gen format is not installed.

---

## Duplicates detection

### Scan a directory for duplicates

```python
from pixopt import scan_duplicates

report = scan_duplicates(
    "./gallery",
    algorithm="phash",
    threshold=5,
    recursive=True,
    hash_size=8,
)

print(f"Scanned: {report.total_files}")
for group in report.duplicate_groups:
    print(f"Group {group.hash_hex}: {group.count} files")
    for f in group.files:
        print(f"  - {f}")
```

### Compute hashes manually

```python
from pixopt import phash, dhash, ahash, hamming_distance, compute_hash

h1 = compute_hash("image1.jpg", algorithm="phash", hash_size=8)
h2 = compute_hash("image2.jpg", algorithm="phash", hash_size=8)

distance = hamming_distance(h1.hash_hex, h2.hash_hex)
print(f"Hamming distance: {distance}")
```

### Find duplicates from a list of hashes

```python
from pathlib import Path
from pixopt import compute_hash, find_duplicates

files = ["image1.jpg", "image2.jpg", "image3.jpg"]
hashes = [compute_hash(f, algorithm="phash", hash_size=8) for f in files]

groups = find_duplicates(hashes, threshold=5)
for group in groups:
    print(f"Hash: {group.hash_hex}")
    for f in group.files:
        print(f"  - {f}")
```

!!! tip
    Use `threshold=0` in `scan_duplicates()` or `find_duplicates()` for exact-duplicate detection. A higher `threshold` catches near-duplicates.

---

## Directory scanning

`scan_directory()` returns a structured inventory of a directory with aggregate statistics.

```python
from pixopt import scan_directory

report = scan_directory(
    "./images",
    recursive=True,
    extensions={".jpg", ".jpeg", ".png", ".webp"},
)

print(f"Total files: {report.total_files}")
print(f"Valid images: {report.valid_images}, Errors: {report.errors}")
print(f"Total size: {report.human_total_size}")
print(f"Largest: {report.largest_file} ({report.largest_size} bytes)")
print("Format breakdown:", report.formats)

for entry in report.entries:
    print(f"{entry.file_path.name}: {entry.width}x{entry.height} {entry.format}")
```

---

## Format benchmark

`benchmark_formats()` encodes an image across multiple formats and quality levels and recommends the smallest successful variant.

```python
from pixopt import benchmark_formats

result = benchmark_formats(
    "photo.jpg",
    qualities=[50, 60, 70, 80, 90],
    formats=["JPEG", "WEBP", "AVIF", "PNG"],
)

for variant in result.variants:
    print(f"{variant.label}: {variant.size_bytes} bytes, saved {variant.savings_percent:.1f}%")

print(f"Recommended: {result.recommended_format} @ q{result.recommended_quality}")
print(f"Recommended size: {result.human_recommended_size}")
```

!!! note
    AVIF is only included if a compatible Pillow plugin (for example `pillow-avif-plugin` or `pillow-heif`) is installed.

---

## Color palette

`extract_palette()` returns the dominant colors of an image.

```python
from pixopt import extract_palette

result = extract_palette("photo.jpg", n=6)

for swatch in result.colors:
    print(f"{swatch.hex} {swatch.rgb} {swatch.percent}%")
```

!!! tip
    `n` must be between 1 and 32. Colors are sorted by frequency, with the most dominant color first.

---

## Base64 and bytes I/O

All image optimization also works in-memory. This is useful for web servers and MCP servers that cannot touch disk.

### Optimize raw bytes

```python
from pixopt import optimize_bytes, OutputFormat

with open("photo.jpg", "rb") as f:
    data = f.read()

result = optimize_bytes(
    data,
    max_width=1200,
    quality=80,
    output_format=OutputFormat.WEBP,
)

print(f"Original: {result.human_original_size}")
print(f"Optimized: {result.human_optimized_size}")
print(f"Success: {result.success}")

# result.data is the optimized image as bytes
open("photo_optimized.webp", "wb").write(result.data)
```

### Optimize base64 strings

```python
import base64
from pixopt import optimize_base64

with open("photo.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("ascii")

result = optimize_base64(
    b64,
    max_width=1200,
    quality=80,
    output_format=OutputFormat.WEBP,
)

if result.success:
    print(f"Output base64 length: {len(result.base64)}")
```

### PIL Image helpers

```python
from PIL import Image
from pixopt import image_to_bytes, image_to_base64, bytes_to_image, base64_to_image

with Image.open("photo.jpg") as img:
    img.load()
    data = image_to_bytes(img, fmt="WEBP", quality=80)
    b64 = image_to_base64(img, fmt="JPEG", quality=85)

img_from_bytes = bytes_to_image(data)
img_from_b64 = base64_to_image(b64)
```

!!! note
    `BytesResult` and `Base64Result` include `original_size`, `optimized_size`, `savings_bytes`, `savings_percent`, `width`, and `height`.

---

## Async API

`pixopt` exposes async variants of the core functions. CPU-bound work is dispatched to a background thread with `asyncio.to_thread` so the event loop stays responsive.

### async optimize image

```python
import asyncio
from pixopt import async_optimize_image, OutputFormat

async def main():
    result = await async_optimize_image(
        "photo.jpg",
        "photo_optimized.webp",
        max_width=1600,
        quality=85,
        output_format=OutputFormat.WEBP,
    )
    print(f"Saved: {result.savings_percent:.1f}%")

asyncio.run(main())
```

### async batch optimize

```python
import asyncio
from pixopt import async_batch_optimize, OutputFormat

async def main():
    report = await async_batch_optimize(
        ["a.jpg", "b.png", "c.webp"],
        "./optimized",
        max_width=1200,
        quality=80,
        output_format=OutputFormat.WEBP,
        max_concurrency=4,
    )
    print(f"Processed {report.succeeded}/{report.total_files}")

asyncio.run(main())
```

### async optimize base64

```python
import asyncio
import base64
from pixopt import async_optimize_base64

async def main():
    with open("photo.jpg", "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    result = await async_optimize_base64(
        b64,
        max_width=1200,
        quality=80,
    )
    print(f"Base64 success: {result.success}")

asyncio.run(main())
```

!!! tip
    The async API mirrors the sync API. Other async helpers include `async_optimize_bytes`, `async_inspect_image`, `async_scan_directory`, and `async_scan_duplicates`.

---

## Advanced: Custom pipelines

Combine multiple features into custom automation scripts. The `Pipeline` class lets you build fluent, chainable workflows.

### Manual pipeline with the optimizer

```python
from pathlib import Path
from pixopt import optimize_image
from pixopt.smart_format import detect_optimal_format

src_dir = Path("./uploads")
out_dir = Path("./optimized")
out_dir.mkdir(parents=True, exist_ok=True)

results = []
for src in src_dir.rglob("*"):
    if not src.is_file():
        continue

    rel = src.relative_to(src_dir)
    fmt = detect_optimal_format(src)

    result = optimize_image(
        src,
        out_dir / rel.with_suffix(f".{fmt.value}"),
        max_width=1600,
        quality=85,
        output_format=fmt,
        strip_metadata=True,
        backup_dir="./uploads_backup",
    )
    results.append(result)

successes = [r for r in results if r.success]
if successes:
    avg = sum(r.savings_percent for r in successes) / len(successes)
    print(f"Processed {len(successes)}/{len(results)} files, avg savings {avg:.1f}%")
```

### Using the `Pipeline` class

```python
from pixopt import Pipeline

result = (
    Pipeline()
    .open("photo.jpg")
    .auto_orient()
    .resize(max_width=1200, fit="cover", aspect_ratio="16:9")
    .watermark_text("(c) pixopt", position="bottom-right", opacity=0.5)
    .optimize(quality=85, output_format="WEBP")
    .save("photo_optimized.webp")
    .run()
)

print(f"Saved to {result.output_path} ({result.size_bytes} bytes)")
print(f"Steps: {result.steps_executed}")
```

You can also chain an image watermark:

```python
from pixopt import Pipeline

result = (
    Pipeline()
    .open("photo.jpg")
    .resize(max_width=1600)
    .watermark_image("logo.png", position="bottom-right", scale=0.2, opacity=0.5)
    .optimize(quality=85, output_format="WEBP")
    .save("photo_watermarked.webp")
    .run()
)
```

!!! note
    `Pipeline.optimize()` accepts `OutputFormat` or a string. `Pipeline.run()` returns a `PipelineResult` with `output_path`, `width`, `height`, `format`, `size_bytes`, and `steps_executed`.

---

## Error handling

Most pixopt functions return a result object with `success` and `error` fields rather than raising exceptions for image-level failures. File-not-found and validation errors still raise.

```python
from pixopt import optimize_image

result = optimize_image("corrupt.jpg", "out.webp")
if not result.success:
    print(f"Failed: {result.error}")
```

!!! warning
    Always check `result.success` in batch, directory, bytes, and base64 workflows. Exceptions are reserved for programmer errors, path traversal attempts, and resource-limit violations.
