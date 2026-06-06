# Library Usage

pixopt can be used as a Python library for custom workflows and integrations. All CLI functionality is exposed through a clean, typed Python API.

---

## Basic optimization

The `optimize_image` function is the core of the library. It handles resizing, format conversion, quality adjustment, and metadata stripping in a single call.

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
print(f"Original size: {result.original_size}")
print(f"Optimized size: {result.optimized_size}")
```

!!! tip
    The `OptimizationResult` object returned by `optimize_image` contains detailed metrics about the optimization, including `savings_percent`, `human_savings`, `original_size`, and `optimized_size`.

---

## Batch / directory processing

Process entire directories with a single function call. The function returns a list of `OptimizationResult` objects, one per file.

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

!!! note
    Files that fail to process (e.g., corrupted images) will have `result.success == False` and an `error` message. The rest of the batch continues uninterrupted.

---

## Format conversion

Convert between any supported format without resizing or quality changes:

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

---

## Lossless compression

Use lossless mode for UI assets, icons, and graphics where pixel-perfect fidelity is required:

```python
from pixopt import optimize_image
from pixopt.models import OutputFormat

result = optimize_image(
    "ui_asset.png",
    "ui_asset.webp",
    output_format=OutputFormat.WEBP,
    lossless=True,
)

# Result will preserve every pixel while still compressing efficiently
```

---

## Adaptive quality (target file size)

Let pixopt find the right quality setting to hit a target file size. This uses binary search under the hood for fast convergence:

```python
from pixopt import optimize_image
from pixopt.models import OutputFormat

result = optimize_image(
    "photo.jpg",
    "photo_optimized.jpg",
    output_format=OutputFormat.JPEG,
    target_size=50,  # Target: 50 KB
)

print(f"Achieved quality: {result.quality}")
print(f"Final size: {result.optimized_size}")
```

!!! note
    `target_size` is specified in **kilobytes (KB)**. The algorithm searches for the highest quality that keeps the file at or below the target size.

---

## Placeholders for lazy loading

Generate three types of placeholders for modern lazy-loading techniques:

```python
from pixopt.placeholder import generate_placeholder

# Dominant color — tiny CSS background color
color = generate_placeholder("photo.jpg", placeholder_type="color")
# → "#3f7a8c"

# LQIP — tiny base64-encoded blurred preview
lqip = generate_placeholder("photo.jpg", placeholder_type="lqip")
# → "data:image/jpeg;base64,/9j/4AAQ..."

# Blurhash — compact string for blurhash-decoder libraries
blurhash = generate_placeholder("photo.jpg", placeholder_type="blurhash")
# → "LEHV6nWB2yk8pyo0adR*.7kCMdnj"
```

!!! tip
    **LQIP** is ideal for immediate visual feedback while images load. **Blurhash** is great if you already use a blurhash decoder in your frontend framework.

---

## Smart format detection

Automatically choose the best format based on image content:

```python
from pixopt.smart_format import detect_optimal_format
from pixopt.models import OutputFormat

fmt = detect_optimal_format("photo.jpg")
# → OutputFormat.WEBP for photographs

fmt = detect_optimal_format("icon.png")
# → OutputFormat.PNG for graphics with few colors

fmt = detect_optimal_format("logo_with_alpha.png")
# → OutputFormat.WEBP for transparent images
```

The detection logic considers:

- **Photographs** → WEBP (best compression for photo detail)
- **Graphics / illustrations** → PNG (preserves sharp edges)
- **Transparent images** → WEBP (supports alpha channel with good compression)

---

## Responsive srcset generation

Generate multiple image variants for responsive `<img srcset="...">` attributes:

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
    print(f"  File: {v.output_path}")
```

This generates:

- `hero-320w.webp`
- `hero-640w.webp`
- `hero-1024w.webp`
- `hero-1920w.webp`

You can then use them in HTML:

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

---

## Backup and min-size filter

Protect originals and skip already-optimized files:

```python
from pixopt import optimize_image

result = optimize_image(
    "photo.jpg",
    "photo_optimized.jpg",
    quality=75,
    backup_dir="./backups",        # Copy original here before processing
    min_size_bytes=10240,           # Skip files below 10 KB
)
```

!!! warning
    If `min_size_bytes` is set and the source file is already smaller, no output file is created and `result.success` will be `False` with a message explaining why.

---

## Favicon generation

Generate multi-resolution ICO favicons from any image:

```python
from pixopt.optimizer import convert_to_favicon

result = convert_to_favicon(
    "logo.png",
    "favicon.ico",
    sizes=[16, 32, 48],
)

print(f"Favicon created: {result.output_path}")
```

---

## Visual comparison

Generate an interactive HTML slider to compare original vs. optimized:

```python
from pixopt.html_comparison import generate_comparison_html

html_path = generate_comparison_html(
    "photo.jpg",
    "photo_optimized.jpg",
    output_path="comparison.html",
)

print(f"Comparison saved to: {html_path}")
```

Open `comparison.html` in a browser to drag a slider and visually inspect the quality difference.

---

## Advanced: Custom pipelines

Combine multiple features into custom automation scripts:

```python
from pathlib import Path
from pixopt import optimize_directory
from pixopt.models import OutputFormat
from pixopt.smart_format import detect_optimal_format

src_dir = Path("./uploads")
out_dir = Path("./optimized")

# Process all uploads with smart format detection
results = optimize_directory(
    src_dir,
    out_dir,
    recursive=True,
    max_width=1600,
    quality=85,
    smart_format=True,
    strip_metadata=True,
    backup_dir="./uploads_backup",
)

# Report summary
total_saved = sum(r.savings_percent for r in results if r.success)
success_count = sum(1 for r in results if r.success)

print(f"Processed {success_count}/{len(results)} files")
print(f"Average savings: {total_saved / success_count:.1f}%")
```
