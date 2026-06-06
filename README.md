# optimg

A powerful, easy-to-use Python library and CLI tool for optimizing images for web and storage.

## Features

- **Size reduction** – resize images to maximum width/height while keeping aspect ratio
- **Format conversion** – convert between JPEG, PNG, WEBP, AVIF, GIF, HEIC/HEIF and SVG
- **Animated GIF → WEBP** – convert animated GIFs to much lighter animated WEBP
- **SVG minification** – pure-Python SVG cleanup (no Node.js tools needed)
- **HEIC/HEIF import** – open iPhone photos directly thanks to `pillow-heif`
- **Lossless mode** – lossless PNG/WEBP compression for UI assets that need pixel-perfect fidelity
- **Adaptive quality** – binary-search quality to hit a target file size automatically
- **Visual comparison** – generate interactive HTML before/after sliders
- **Responsive srcset** – generate multiple width variants and HTML `<img srcset="...">` snippets
- **Lazy-loading placeholders** – extract dominant color, generate LQIP data URIs, or blurhash strings
- **Smart format detection** – auto-detect the most efficient format (photo → WEBP, graphic → PNG, transparent → WEBP)
- **Backup originals** – copy originals to a backup directory before processing
- **Min-size filter** – skip files already below a size threshold
- **Metadata stripping** – remove EXIF and other metadata to save space
- **Quality tuning** – adjustable compression quality (1-100)
- **Progressive JPEG** – enable progressive encoding for better web delivery
- **Batch processing** – optimize single files, directories, or multiple files at once
- **CLI with Typer** – intuitive command-line interface with beautiful output

## Installation

```bash
pip install optimg
```

## CLI Usage

### Optimize a single image

```bash
optimg optimize photo.jpg photo_optimized.jpg --quality 80 --width 1200
```

### Optimize all images in a directory

```bash
optimg optimize ./images ./optimized --recursive --quality 85 --format webp
```

### Batch optimize specific files

```bash
optimg batch photo1.jpg photo2.png photo3.bmp -o ./optimized --width 800
```

### Convert image format / extension

```bash
optimg convert photo.png photo.webp -f webp
optimg convert ./images ./webp_images -r -f webp
```

### Generate favicon (.ico)

```bash
optimg favicon logo.png favicon.ico
optimg favicon logo.png --size 16 --size 32 --size 48
```

### Convert animated GIF to animated WEBP

```bash
optimg convert animation.gif animation.webp -f webp
```

### Optimize SVG

```bash
optimg convert icon.svg icon.min.svg
```

### Convert HEIC (iPhone) to JPEG

```bash
optimg convert photo.heic photo.jpg
```

### Lossless PNG/WEBP for UI assets

```bash
optimg convert icon.png icon.webp --lossless -f webp
```

### Adaptive quality (target file size)

```bash
optimg optimize photo.jpg --target-size 50
```

### Generate visual comparison HTML

```bash
optimg compare photo.jpg comparison.html --open
```

### Generate responsive srcset images

```bash
optimg srcset hero.jpg --sizes 320,640,1024,1920 --output-dir ./responsive/
optimg srcset hero.jpg --sizes 320,640,1024,1920 -f webp --html snippet.html
```

### Generate lazy-loading placeholders

```bash
optimg placeholder photo.jpg --type color
optimg placeholder photo.jpg --type lqip
optimg placeholder photo.jpg --type blurhash -o blurhash.txt
```

### Smart format detection

```bash
optimg optimize photo.jpg --smart-format
optimg convert graphic.png output --smart-format
```

### Backup originals before processing

```bash
optimg optimize ./images --backup ./originals --recursive
```

### Skip already-optimized files

```bash
optimg optimize ./images --min-size 10 --recursive
```

### Inspect image info without optimizing

```bash
optimg info photo.jpg
```

### Available options

| Option | Description |
|--------|-------------|
| `-q, --quality` | JPEG/WEBP quality (1-100, default: 85) |
| `-w, --width` | Maximum width in pixels |
| `-h, --height` | Maximum height in pixels |
| `-f, --format` | Output format: auto, jpeg, png, webp, avif, original |
| `-s, --strip` | Remove metadata (default: True) |
| `--progressive` | Progressive JPEG encoding (default: True) |
| `-r, --recursive` | Process directories recursively |
| `--overwrite` | Overwrite source files |
| `--lossless` | Lossless PNG/WEBP compression |
| `--target-size` | Target file size in KB (adaptive quality) |
| `--smart-format` | Auto-detect the most efficient output format |
| `--backup` | Backup originals to this directory |
| `--min-size` | Skip files already smaller than this threshold (KB) |

## Library Usage

```python
from optimg import optimize_image
from optimg.models import OutputFormat

# Optimize a single image
result = optimize_image(
    "photo.jpg",
    "photo_optimized.webp",
    max_width=1200,
    quality=80,
    strip_metadata=True,
    output_format=OutputFormat.WEBP,
)

print(f"Saved {result.savings_percent:.1f}% ({result.human_savings})")
```

### Placeholders for lazy loading

```python
from optimg.placeholder import generate_placeholder

color = generate_placeholder("photo.jpg", placeholder_type="color")
lqip = generate_placeholder("photo.jpg", placeholder_type="lqip")
blurhash = generate_placeholder("photo.jpg", placeholder_type="blurhash")
```

### Smart format detection

```python
from optimg.smart_format import detect_optimal_format

fmt = detect_optimal_format("photo.jpg")
# Returns OutputFormat.WEBP for photos, PNG for graphics, WEBP for transparent images
```

### Responsive srcset generation

```python
from optimg.srcset_generator import generate_srcset_images

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

### Batch / directory processing

```python
from optimg import optimize_directory

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
```

## Development

Install in development mode:

```bash
git clone https://github.com/yourusername/optimg.git
cd optimg
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run linter:

```bash
ruff check src tests
mypy src
```

Build documentation locally:

```bash
pip install -e ".[docs]"
mkdocs serve
```

## License

MIT
