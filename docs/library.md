# Library Usage

pixopt can be used as a Python library for custom workflows and integrations.

## Basic optimization

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

## Batch / directory processing

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

## Format conversion

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

## Lossless compression

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

## Adaptive quality (target file size)

```python
from pixopt import optimize_image
from pixopt.models import OutputFormat

result = optimize_image(
    "photo.jpg",
    "photo_optimized.jpg",
    output_format=OutputFormat.JPEG,
    target_size=50,  # KB
)
```

## Placeholders for lazy loading

```python
from pixopt.placeholder import generate_placeholder

# Dominant color
color = generate_placeholder("photo.jpg", placeholder_type="color")
# → "#3f7a8c"

# Low-quality image placeholder (base64 data URI)
lqip = generate_placeholder("photo.jpg", placeholder_type="lqip")
# → "data:image/jpeg;base64,/9j/4AAQ..."

# Blurhash
blurhash = generate_placeholder("photo.jpg", placeholder_type="blurhash")
# → "LEHV6nWB2yk8pyo0adR*.7kCMdnj"
```

## Smart format detection

```python
from pixopt.smart_format import detect_optimal_format

fmt = detect_optimal_format("photo.jpg")
# Returns OutputFormat.WEBP for photos, PNG for graphics, WEBP for transparent images
```

## Responsive srcset generation

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

## Backup and min-size filter

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

## Favicon generation

```python
from pixopt.optimizer import convert_to_favicon

result = convert_to_favicon(
    "logo.png",
    "favicon.ico",
    sizes=[16, 32, 48],
)
```
