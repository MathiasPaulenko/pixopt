# CLI Usage

The CLI is built with [Typer](https://typer.tiangolo.com/) and provides an intuitive interface for all optimization features. Every command supports `--help` for detailed usage information.

---

## Global options

These options are available for most commands that process images:

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--quality` | `-q` | JPEG/WEBP quality (1–100) | `85` |
| `--width` | `-w` | Maximum width in pixels | — |
| `--height` | `-h` | Maximum height in pixels | — |
| `--format` | `-f` | Output format: `auto`, `jpeg`, `png`, `webp`, `avif`, `original` | `auto` |
| `--strip` | `-s` | Remove metadata (EXIF, ICC, etc.) | `True` |
| `--progressive` | — | Progressive JPEG encoding | `True` |
| `--recursive` | `-r` | Process directories recursively | `False` |
| `--overwrite` | — | Overwrite source files in place | `False` |
| `--lossless` | — | Lossless PNG/WEBP compression | `False` |
| `--target-size` | — | Target file size in KB (adaptive quality) | — |
| `--smart-format` | — | Auto-detect the most efficient output format | `False` |
| `--backup` | — | Backup originals to this directory | — |
| `--min-size` | — | Skip files already smaller than this threshold (KB) | — |

---

## Commands

### `optimize`

Optimize a single image or all images in a directory. This is the main command for everyday use.

**Syntax:**

```bash
pixopt optimize [SOURCE] [DESTINATION] [OPTIONS]
```

**Examples:**

```bash
# Optimize a single image
pixopt optimize photo.jpg photo_optimized.jpg --quality 80 --width 1200

# Optimize an entire directory recursively
pixopt optimize ./images ./optimized --recursive --quality 85 --format webp

# Overwrite originals in place
pixopt optimize ./images --recursive --overwrite

# Backup originals before processing
pixopt optimize ./images ./optimized --recursive --backup ./originals

# Skip files already below 10 KB
pixopt optimize ./images ./optimized --recursive --min-size 10

# Target a specific file size (adaptive quality)
pixopt optimize photo.jpg photo_optimized.jpg --target-size 50

# Smart format detection
pixopt optimize photo.jpg photo_optimized.jpg --smart-format
```

**Command-specific options:**

| Option | Description |
|--------|-------------|
| `source` | Input file or directory |
| `destination` | Output file or directory |

---

### `batch`

Optimize multiple specific files at once. Unlike `optimize`, `batch` takes a list of files rather than a directory.

**Syntax:**

```bash
pixopt batch [FILES...] -o [OUTPUT_DIR] [OPTIONS]
```

**Examples:**

```bash
# Optimize specific files into a directory
pixopt batch photo1.jpg photo2.png photo3.bmp -o ./optimized --width 800

# Mixed formats with smart detection
pixopt batch photo.jpg icon.png logo.svg -o ./assets --smart-format --quality 90
```

**Command-specific options:**

| Option | Short | Description |
|--------|-------|-------------|
| `-o, --output-dir` | `-o` | Output directory (required) |

---

### `convert`

Convert an image to a different format or extension. Supports format change, resizing, and all optimization options in one step.

**Syntax:**

```bash
pixopt convert [SOURCE] [DESTINATION] [OPTIONS]
```

**Examples:**

```bash
# Convert PNG to WEBP
pixopt convert photo.png photo.webp -f webp

# Convert an entire directory to WEBP
pixopt convert ./images ./webp_images -r -f webp

# Convert animated GIF to animated WEBP
pixopt convert animation.gif animation.webp -f webp

# Convert HEIC (iPhone) to JPEG
pixopt convert photo.heic photo.jpg

# Optimize SVG
pixopt convert icon.svg icon.min.svg

# Lossless conversion for UI assets
pixopt convert icon.png icon.webp --lossless -f webp

# Smart format detection
pixopt convert graphic.png output --smart-format
```

---

### `favicon`

Convert an image to a multi-resolution ICO favicon.

**Syntax:**

```bash
pixopt favicon [SOURCE] [DESTINATION] --size [SIZE]...
```

**Examples:**

```bash
# Default sizes (16, 32, 48)
pixopt favicon logo.png favicon.ico

# Custom sizes
pixopt favicon logo.png favicon.ico --size 16 --size 32 --size 48 --size 64
```

**Command-specific options:**

| Option | Description |
|--------|-------------|
| `--size` | Favicon size to include (can be repeated) |

---

### `info`

Inspect image metadata without optimizing. Displays dimensions, format, mode, and file size.

**Syntax:**

```bash
pixopt info [FILE]
```

**Example:**

```bash
pixopt info photo.jpg
```

**Sample output:**

```
File: photo.jpg
Dimensions: 4032 x 3024
Format: JPEG
Mode: RGB
File size: 4.2 MB
```

---

### `compare`

Generate an interactive HTML before/after slider to visually compare the original and optimized images.

**Syntax:**

```bash
pixopt compare [SOURCE] [OUTPUT_HTML] [OPTIONS]
```

**Examples:**

```bash
# Generate comparison and open in browser
pixopt compare photo.jpg comparison.html --open

# Generate comparison with specific quality settings
pixopt compare photo.jpg comparison.html --quality 70 --width 1200
```

**Command-specific options:**

| Option | Description |
|--------|-------------|
| `--open` | Open the generated HTML in the default browser |

---

### `srcset`

Generate responsive image variants and an HTML `<img srcset="...">` snippet.

**Syntax:**

```bash
pixopt srcset [SOURCE] --sizes [SIZES] [OPTIONS]
```

**Examples:**

```bash
# Generate variants and output to directory
pixopt srcset hero.jpg --sizes 320,640,1024,1920 --output-dir ./responsive/

# Generate variants with HTML snippet
pixopt srcset hero.jpg --sizes 320,640,1024,1920 -f webp --html snippet.html

# Generate with custom quality
pixopt srcset hero.jpg --sizes 400,800,1200 --quality 80 --output-dir ./responsive/
```

**Command-specific options:**

| Option | Description |
|--------|-------------|
| `--sizes` | Comma-separated list of widths |
| `--output-dir` | Directory to write responsive images |
| `--html` | Path to write the HTML srcset snippet |

---

### `placeholder`

Extract a placeholder for lazy loading. Supports three types: dominant color, LQIP (low-quality image placeholder), and blurhash.

**Syntax:**

```bash
pixopt placeholder [SOURCE] --type [TYPE] [OPTIONS]
```

**Examples:**

```bash
# Dominant color (hex string)
pixopt placeholder photo.jpg --type color
# → "#3f7a8c"

# LQIP data URI (base64 JPEG)
pixopt placeholder photo.jpg --type lqip
# → "data:image/jpeg;base64,/9j/4AAQ..."

# Blurhash string
pixopt placeholder photo.jpg --type blurhash -o blurhash.txt
# → "LEHV6nWB2yk8pyo0adR*.7kCMdnj"
```

**Command-specific options:**

| Option | Description |
|--------|-------------|
| `--type` | Placeholder type: `color`, `lqip`, `blurhash` |
| `-o, --output` | Write output to file instead of stdout |

---

## Use-case recipes

### Web asset pipeline

Convert all images in a directory to optimized WEBP with backups:

```bash
pixopt optimize ./static/images ./static/optimized \
  --recursive \
  --format webp \
  --quality 85 \
  --width 1920 \
  --backup ./static/originals \
  --strip
```

### E-commerce product images

Generate responsive srcset for product galleries:

```bash
pixopt srcset product.jpg \
  --sizes 320,640,960,1280 \
  --output-dir ./product-gallery/ \
  --html product-gallery.html \
  --quality 90
```

### Blog image optimization

Optimize blog images with smart format detection and skip small files:

```bash
pixopt optimize ./blog/images ./blog/optimized \
  --recursive \
  --smart-format \
  --min-size 5 \
  --width 1200
```

### UI icon set (lossless)

Convert icons to lossless WEBP for pixel-perfect rendering:

```bash
pixopt convert ./icons ./icons-webp \
  --recursive \
  --lossless \
  --format webp
```

### Social media thumbnails

Target exact file size for platform requirements:

```bash
pixopt optimize thumbnail.jpg thumbnail_optimized.jpg --target-size 200
```

### iPhone photo batch conversion

Convert HEIC photos to JPEG for compatibility:

```bash
pixopt convert ./iphone_photos ./jpeg_photos \
  --recursive \
  --format jpeg \
  --quality 95
```
