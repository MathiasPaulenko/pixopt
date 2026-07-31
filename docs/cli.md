# CLI Usage

The CLI is built with [Typer](https://typer.tiangolo.com/) and provides an intuitive interface for all optimization features. The entry point is `pixopt`, and every command supports `--help` for detailed usage information.

---

## Global options

These options are available for most commands that process images:

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `--quality` | `-q` | JPEG/WEBP quality (1–100) | `85` |
| `--width` | `-w` | Maximum width in pixels | — |
| `--height` | `-h` | Maximum height in pixels | — |
| `--format` | `-f` | Output format: `auto`, `jpeg`, `png`, `webp`, `avif`, `original` | `auto` |
| `--strip` | `-s` | Remove metadata (EXIF, ICC, etc.) | `True` |
| `--progressive` | — | Progressive JPEG encoding | `True` |
| `--recursive` | `-r` | Process directories recursively | `False` |
| `--overwrite` | — | Overwrite existing output files | `False` |
| `--lossless` | — | Lossless PNG/WEBP compression | `False` |
| `--target-size` | — | Target file size in KB (adaptive quality) | — |
| `--smart-format` | — | Auto-detect the most efficient output format | `False` |
| `--backup` | — | Backup originals to this directory | — |
| `--min-size` | — | Skip files already smaller than this threshold (KB) | — |

!!! tip "Getting help"
    Run `pixopt --help` to list all commands, and `pixopt <command> --help` to see the exact options and defaults for a specific command.

!!! note "Per-command options"
    Many commands also accept additional common options such as `--fit`, `--anchor`, `--aspect-ratio`, `--background-color`, `--auto-orient`, `--optimize`, `--preset`, and `--output {table|json}`. These are documented in the command-specific tables below.

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

# Smart format detection for a single file
pixopt optimize photo.jpg photo_optimized.jpg --smart-format

# Crop to a square using cover fit with face anchor
pixopt optimize photo.jpg photo_square.jpg --fit cover --anchor face --aspect-ratio 1:1

# Keep selected EXIF groups while stripping other metadata
pixopt optimize photo.jpg photo_optimized.jpg --keep-exif orientation --keep-exif copyright

# Use a built-in preset
pixopt optimize photo.jpg photo_optimized.jpg --preset web

# Output the result report as JSON
pixopt optimize ./images ./optimized --recursive --output json
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` | — | Input file or directory | required |
| `DESTINATION` | — | Output file or directory; omitted for in-place directory processing | — |
| `--width` | `-w` | Maximum width in pixels | — |
| `--height` | `-h` | Maximum height in pixels | — |
| `--quality` | `-q` | JPEG/WEBP quality (1–100) | `85` |
| `--format` | `-f` | Output format: `auto`, `jpeg`, `png`, `webp`, `avif`, `original` | `auto` |
| `--fit` | — | Resize fit mode: `down`, `cover`, `contain`, `fill` | — |
| `--anchor` | `-a` | Anchor for cover/contain: `center`, `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right`, `face` | `center` |
| `--aspect-ratio` / `--ar` | — | Target aspect ratio, e.g. `16:9` or `4/3` | — |
| `--background-color` / `--bg` | — | Background color for contain padding, e.g. `white` or `#ffffff` | `white` |
| `--auto-orient` / `--keep-orientation` | — | Apply EXIF orientation before processing | `True` |
| `--strip` / `--keep-metadata` | `-s` / `-k` | Remove EXIF and metadata | `True` |
| `--progressive` / `--baseline` | — | Progressive JPEG encoding | `True` |
| `--optimize` / `--no-optimize` | — | Enable Pillow optimizer | `True` |
| `--lossless` | — | Use lossless PNG/WEBP compression | `False` |
| `--recursive` | `-r` | Process directories recursively | `False` |
| `--overwrite` | — | Overwrite existing output files | `False` |
| `--target-size` | — | Target file size in KB (adaptive quality search) | — |
| `--smart-format` | — | Auto-detect the most efficient output format for a single file | `False` |
| `--backup` | — | Backup originals to this directory | — |
| `--min-size` | — | Skip files already smaller than this threshold (KB) | — |
| `--keep-exif` | — | EXIF groups to keep when stripping metadata (repeatable) | — |
| `--preset` | `-p` | Apply a named preset: `web`, `social`, `thumbnail`, `e-commerce`, `print` | — |
| `--preset-file` | — | Load custom presets from a JSON file | — |
| `--output` | — | Result display format: `table` or `json` | `table` |

!!! note
    `--target-size` performs an adaptive quality search and works best with JPEG and WEBP output. `--smart-format` only applies when `SOURCE` is a single file.

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

# Mixed formats into a directory
pixopt batch photo.jpg icon.png logo.svg -o ./assets --quality 90

# Resize a set of images to a fixed thumbnail size
pixopt batch *.jpg -o ./thumbnails --width 400 --height 400 --fit cover

# Backup originals and get a JSON report
pixopt batch photo1.jpg photo2.jpg -o ./optimized --backup ./originals --output json
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `FILES...` | — | Source image files | required |
| `--output-dir` | `-o` | Output directory for all processed images | `./optimized` |
| `--width` | `-w` | Maximum width in pixels | — |
| `--height` | `-h` | Maximum height in pixels | — |
| `--quality` | `-q` | JPEG/WEBP quality (1–100) | `85` |
| `--format` | `-f` | Output format | `auto` |
| `--strip` / `--keep-metadata` | `-s` / `-k` | Remove EXIF and metadata | `True` |
| `--progressive` / `--baseline` | — | Progressive JPEG encoding | `True` |
| `--optimize` / `--no-optimize` | — | Enable Pillow optimizer | `True` |
| `--lossless` | — | Use lossless PNG/WEBP compression | `False` |
| `--backup` | — | Backup originals to this directory | — |
| `--min-size` | — | Skip files already smaller than this threshold (KB) | — |
| `--output` | — | Report format: `table` or `json` | `table` |

!!! note
    The `--output` option only controls the terminal report format; the `--output-dir` option sets where the processed images are written.

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
pixopt convert graphic.png output.webp --smart-format

# Fit inside a box with a white background
pixopt convert photo.jpg photo.png --fit contain --width 800 --height 600 --background-color white
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` | — | Input file or directory | required |
| `DESTINATION` | — | Output file or directory | — |
| `--width` | `-w` | Maximum width in pixels | — |
| `--height` | `-h` | Maximum height in pixels | — |
| `--quality` | `-q` | JPEG/WEBP quality (1–100) | `85` |
| `--format` | `-f` | Output format: `auto`, `jpeg`, `png`, `webp`, `avif`, `original` | `auto` |
| `--fit` | — | Resize fit mode: `down`, `cover`, `contain`, `fill` | — |
| `--anchor` | `-a` | Anchor for cover/contain | `center` |
| `--aspect-ratio` / `--ar` | — | Target aspect ratio, e.g. `16:9` | — |
| `--background-color` / `--bg` | — | Background color for contain padding | `white` |
| `--auto-orient` / `--keep-orientation` | — | Apply EXIF orientation before processing | `True` |
| `--strip` / `--keep-metadata` | `-s` / `-k` | Remove EXIF and metadata | `True` |
| `--progressive` / `--baseline` | — | Progressive JPEG encoding | `True` |
| `--optimize` / `--no-optimize` | — | Enable Pillow optimizer | `True` |
| `--lossless` | — | Use lossless PNG/WEBP compression | `False` |
| `--recursive` | `-r` | Process directories recursively | `False` |
| `--overwrite` | — | Overwrite existing output files | `False` |
| `--smart-format` | — | Auto-detect the most efficient output format for a single file | `False` |
| `--backup` | — | Backup originals to this directory | — |
| `--min-size` | — | Skip files already smaller than this threshold (KB) | — |
| `--preset` | `-p` | Apply a named preset | — |
| `--preset-file` | — | Load custom presets from a JSON file | — |
| `--output` | — | Result display format: `table` or `json` | `table` |

---

### `favicon`

Convert an image to a multi-resolution ICO favicon.

**Syntax:**

```bash
pixopt favicon [SOURCE] [DESTINATION] [OPTIONS]
```

**Examples:**

```bash
# Default sizes (16, 32, 48, 64, 128, 256)
pixopt favicon logo.png favicon.ico

# Custom sizes
pixopt favicon logo.png favicon.ico --size 16 --size 32 --size 48 --size 64

# Preserve transparency
pixopt favicon logo.png favicon.ico --keep-transparency

# Fill transparent background
pixopt favicon logo-transparent.png favicon.ico --fill-background
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` | — | Source image file | required |
| `DESTINATION` | — | Output `.ico` path; defaults to source stem with `.ico` | — |
| `--size` | — | Square size to include in the ICO; can be repeated | `16,32,48,64,128,256` |
| `--keep-transparency` / `--fill-background` | — | Preserve alpha channel or fill with background | `True` |

---

### `info`

Inspect image metadata without optimizing. Displays dimensions, format, mode, file size, DPI, alpha, animation, ICC profile, orientation, and EXIF.

**Syntax:**

```bash
pixopt info [FILE] [OPTIONS]
```

**Examples:**

```bash
pixopt info photo.jpg
pixopt info photo.jpg --json
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `FILE` | — | Image file to inspect | required |
| `--json` | — | Output metadata as JSON | `False` |

**Sample output:**

```text
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

# Generate lossless WEBP comparison
pixopt compare photo.jpg report.html --format webp --lossless
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` | — | Source image file | required |
| `OUTPUT_HTML` | — | Output HTML comparison file | `comparison.html` |
| `--open` / `--no-open` | — | Open the generated HTML in the default browser | `False` |
| `--width` | `-w` | Maximum width of the optimized image | — |
| `--height` | `-h` | Maximum height of the optimized image | — |
| `--quality` | `-q` | JPEG/WEBP quality (1–100) | `85` |
| `--format` | `-f` | Output format | `auto` |
| `--strip` / `--keep-metadata` | `-s` / `-k` | Remove metadata | `True` |
| `--progressive` / `--baseline` | — | Progressive JPEG encoding | `True` |
| `--optimize` / `--no-optimize` | — | Enable Pillow optimizer | `True` |
| `--lossless` | — | Use lossless PNG/WEBP compression | `False` |

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

# AVIF variants for a gallery
pixopt srcset hero.jpg --sizes 480,960,1440,1920 -f avif --lossless --html gallery.html
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` | — | Source image file | required |
| `--sizes` | `-s` | Comma-separated target widths in pixels | required |
| `--output-dir` | `-o` | Directory to write responsive images | `./output/responsive` |
| `--format` | `-f` | Output format: `webp`, `jpeg`, `png`, `avif` | `webp` |
| `--quality` | `-q` | JPEG/WEBP quality (1–100) | `85` |
| `--strip` / `--keep-metadata` | `-s` / `-k` | Remove metadata | `True` |
| `--progressive` / `--baseline` | — | Progressive JPEG encoding | `True` |
| `--optimize` / `--no-optimize` | — | Enable Pillow optimizer | `True` |
| `--lossless` | — | Use lossless PNG/WEBP compression | `False` |
| `--html` | — | Path to write the HTML srcset snippet | — |

!!! warning "Short option collision"
    `--sizes` uses `-s`. Because `--strip` also declares a `-s` short flag in this command, prefer the full option names (`--sizes`, `--strip`) to avoid ambiguity.

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
# outputs "#3f7a8c"

# LQIP data URI (base64 JPEG)
pixopt placeholder photo.jpg --type lqip
# outputs "data:image/jpeg;base64,/9j/4AAQ..."

# Blurhash string
pixopt placeholder photo.jpg --type blurhash -o blurhash.txt
# outputs "LEHV6nWB2yk8pyo0adR*.7kCMdnj"

# Larger LQIP with higher JPEG quality
pixopt placeholder photo.jpg --type lqip --lqip-size 64 --lqip-quality 30
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` | — | Source image file | required |
| `--type` | `-t` | Placeholder type: `color`, `lqip`, `blurhash` | `color` |
| `--output` | `-o` | Write output to file instead of stdout | — |
| `--lqip-size` | — | LQIP thumbnail max dimension in pixels | `32` |
| `--lqip-quality` | — | LQIP JPEG quality (1–100) | `20` |

---

### `watermark`

Add a text or image watermark to an image.

**Syntax:**

```bash
pixopt watermark [SOURCE] [OUTPUT] [OPTIONS]
```

**Examples:**

```bash
# Text watermark
pixopt watermark photo.jpg photo_watermarked.jpg --text "Copyright 2024"

# Text with custom position and opacity
pixopt watermark photo.jpg photo_watermarked.jpg --text "Demo" --position top-right --opacity 0.3

# Image watermark
pixopt watermark photo.jpg photo_watermarked.jpg --watermark-image logo.png --scale 0.2 --position bottom-left

# Custom font and size
pixopt watermark photo.jpg photo_watermarked.jpg --text "Logo" --font-path Roboto.ttf --font-size 48 --padding 30

# JSON report
pixopt watermark photo.jpg photo_watermarked.jpg --watermark-image stamp.png --opacity 0.7 --output json
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` | — | Source image file | required |
| `OUTPUT` | — | Output image path | required |
| `--text` | `-t` | Text watermark content | — |
| `--watermark-image` | `-w` | Watermark image (PNG with alpha recommended) | — |
| `--position` | `-p` | Watermark position | `bottom-right` |
| `--opacity` | — | Opacity from `0.0` to `1.0` | `0.5` |
| `--padding` | — | Padding from edge in pixels | `20` |
| `--font-size` | — | Font size for text watermark | `36` |
| `--scale` | — | Scale factor for image watermark relative to base width | — |
| `--font-path` | — | Path to a TTF/OTF font file | — |
| `--output` | — | Result display format: `table` or `json` | `table` |

!!! note
    You must provide either `--text` or `--watermark-image`, but not both.

---

### `sprite`

Combine images into a sprite sheet or contact sheet.

**Syntax:**

```bash
pixopt sprite [OUTPUT] [IMAGES...] [OPTIONS]
```

**Examples:**

```bash
# Simple grid sprite
pixopt sprite icons.png icon1.png icon2.png icon3.png

# Fixed column grid with padding
pixopt sprite icons.png icon*.png --layout grid --columns 4 --padding 10

# Horizontal strip in WEBP
pixopt sprite flags.png flag_*.png --layout horizontal --format webp

# Contact sheet with labels
pixopt sprite contact.png img1.jpg img2.jpg img3.jpg --contact-sheet --columns 3 --format png
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `OUTPUT` | — | Output sprite sheet path | required |
| `IMAGES...` | — | Image files to combine | required |
| `--cell-width` | — | Width of each cell in pixels | — |
| `--cell-height` | — | Height of each cell in pixels | — |
| `--columns` | `-c` | Number of columns (grid layout) | — |
| `--layout` | `-l` | Layout: `grid`, `horizontal`, `vertical` | `grid` |
| `--padding` | `-p` | Pixels between cells | `0` |
| `--contact-sheet` | — | Create a contact sheet with labels instead of a sprite | `False` |
| `--format` | `-f` | Output image format: `PNG`, `JPEG`, `WEBP` | `PNG` |
| `--json` | — | Output results as JSON | `False` |

!!! note
    In `--contact-sheet` mode, `cell-width` and `cell-height` default to `200` if not provided.

---

### `bundle`

Generate a complete set of web assets from one source image. Produces hero, thumbnail, `og:image`, favicon, srcset variants, LQIP, blurhash, palette, and dominant color.

**Syntax:**

```bash
pixopt bundle [SOURCE] [OPTIONS]
```

**Examples:**

```bash
# Generate all assets with defaults
pixopt bundle hero.jpg

# Custom output directory and sizes
pixopt bundle hero.jpg -o ./assets --hero-width 1600 --thumbnail-width 240

# Skip selected assets
pixopt bundle hero.jpg -o ./assets --no-favicon --no-blurhash

# Get a JSON report
pixopt bundle hero.jpg --quality 90 --palette-n 8 --output json
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` | — | Source image file | required |
| `--output-dir` | `-o` | Output directory for all generated assets | `./assets` |
| `--quality` | `-q` | JPEG/WEBP quality for generated images | `85` |
| `--hero-width` | — | Hero image max width in pixels | `1920` |
| `--thumbnail-width` | — | Thumbnail max width in pixels | `300` |
| `--og-width` | — | `og:image` width in pixels | `1200` |
| `--og-height` | — | `og:image` height in pixels | `630` |
| `--palette-n` | — | Number of palette colors to extract | `6` |
| `--no-hero` | — | Skip hero image generation | `False` |
| `--no-thumbnail` | — | Skip thumbnail generation | `False` |
| `--no-og` | — | Skip `og:image` generation | `False` |
| `--no-favicon` | — | Skip favicon generation | `False` |
| `--no-srcset` | — | Skip srcset generation | `False` |
| `--no-lqip` | — | Skip LQIP generation | `False` |
| `--no-blurhash` | — | Skip blurhash generation | `False` |
| `--no-palette` | — | Skip palette extraction | `False` |
| `--no-dominant-color` | — | Skip dominant color extraction | `False` |
| `--output` | — | Report format: `table` or `json` | `table` |

---

### `pdf`

Convert PDF pages to images, or combine images into a single PDF.

**Syntax:**

```bash
# Import: PDF to images
pixopt pdf [SOURCE] [OPTIONS]

# Export: images to PDF
pixopt pdf [OUTPUT] --from-images [IMAGES...] [OPTIONS]
```

**Examples:**

```bash
# Extract pages as JPEG at 200 DPI
pixopt pdf document.pdf -o ./pages --dpi 200 --format jpeg

# Extract pages as PNG with defaults
pixopt pdf document.pdf --dpi 150 --format png

# Combine images into a PDF
pixopt pdf output.pdf --from-images page1.png page2.png page3.png -o output.pdf

# Combine all scans into a single PDF
pixopt pdf scans.pdf --from-images scan*.png -o scans.pdf
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` / `OUTPUT` | — | PDF file to import, or output PDF path for export | required |
| `--output` | `-o` | Output directory (import) or output PDF file (export) | — |
| `--dpi` | — | Render resolution in DPI | `150` |
| `--format` | `-f` | Output image format for import: `PNG`, `JPEG`, `WEBP` | `PNG` |
| `--from-images` | — | Image files to combine into a PDF; repeat for multiple | — |
| `--json` | — | Output results as JSON | `False` |

!!! warning
    PDF support requires the optional dependency `PyMuPDF` (`fitz`). Install the `pdf` extra, or the command will fail at runtime.

!!! note
    When importing, the default output directory is the source PDF's stem directory. When exporting, the default output PDF is the `SOURCE` argument with the `.pdf` extension.

---

### `nextgen`

Detect or convert images to next-generation formats (JXL, WEBP2).

**Syntax:**

```bash
# Detect support
pixopt nextgen [ACTION] [SOURCE] [OPTIONS]
```

**Examples:**

```bash
# Show next-gen format support
pixopt nextgen detect

# Show support as JSON
pixopt nextgen detect --json

# Convert to JXL
pixopt nextgen convert photo.jpg -o photo.jxl --format jxl --quality 85

# Convert without fallback
pixopt nextgen convert photo.jpg -o photo.jxl --format jxl --no-fallback

# Convert to WEBP2
pixopt nextgen convert photo.jpg -o photo.webp2 --format webp2 --quality 90
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `ACTION` | — | `detect` or `convert` | `detect` |
| `SOURCE` | — | Source image (required for `convert`) | — |
| `--output` | `-o` | Output path for converted image | — |
| `--format` | `-f` | Target format: `jxl` or `webp2` | `jxl` |
| `--quality` | `-q` | Quality (1–100) | `85` |
| `--no-fallback` | — | Disable fallback to fallback format | `False` |
| `--fallback-format` | — | Fallback format when target is not supported | `webp` |
| `--json` | — | Output results as JSON | `False` |

!!! tip
    Run `pixopt nextgen detect` first to see whether the required encoder plugins are installed on your system.

---

### `duplicates`

Find duplicate or near-duplicate images in a directory using perceptual hashing.

**Syntax:**

```bash
pixopt duplicates [DIRECTORY] [OPTIONS]
```

**Examples:**

```bash
# Default pHash scan
pixopt duplicates ./images

# Exact duplicates only
pixopt duplicates ./images --recursive --threshold 0

# Use dHash with a high threshold
pixopt duplicates ./images -a dhash -t 10 -r

# JSON report
pixopt duplicates ./images --json
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `DIRECTORY` | — | Directory to scan | required |
| `--algorithm` | `-a` | Hash algorithm: `phash`, `dhash`, `ahash` | `phash` |
| `--threshold` | `-t` | Maximum Hamming distance for duplicates (0 = exact) | `5` |
| `--recursive` | `-r` | Scan subdirectories recursively | `False` |
| `--json` | — | Output results as JSON | `False` |

!!! note
    A threshold of `0` finds exact duplicates. Larger values include visually similar images.

---

### `scan`

Scan a directory and show an inventory of images with aggregate statistics.

**Syntax:**

```bash
pixopt scan [DIRECTORY] [OPTIONS]
```

**Examples:**

```bash
pixopt scan ./images
pixopt scan ./images --recursive
pixopt scan ./images -r --json
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `DIRECTORY` | — | Directory to scan | required |
| `--recursive` | `-r` | Scan subdirectories recursively | `False` |
| `--json` | — | Output results as JSON | `False` |

---

### `benchmark`

Benchmark an image across multiple formats and quality levels to find the best compression settings.

**Syntax:**

```bash
pixopt benchmark [SOURCE] [OPTIONS]
```

**Examples:**

```bash
# Benchmark with defaults
pixopt benchmark photo.jpg

# Custom quality levels
pixopt benchmark photo.jpg -q 70 -q 80 -q 90

# Compare only WEBP and AVIF
pixopt benchmark photo.jpg -f webp -f avif -q 80

# JSON output
pixopt benchmark photo.jpg --json
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` | — | Source image file | required |
| `--quality` | `-q` | Quality level(s) to benchmark; repeat for multiple | `50,60,70,80,90` |
| `--format` | `-f` | Format(s) to benchmark; repeat for multiple | `JPEG,WEBP,AVIF,PNG` |
| `--json` | — | Output benchmark results as JSON | `False` |

!!! tip
    Use `benchmark` before picking a format for a large batch. The last row of the table marks the recommended format and quality combination.

---

### `palette`

Extract the dominant colors from an image as a color palette.

**Syntax:**

```bash
pixopt palette [SOURCE] [OPTIONS]
```

**Examples:**

```bash
pixopt palette photo.jpg
pixopt palette photo.jpg --count 8
pixopt palette photo.jpg -n 12 --json
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `SOURCE` | — | Source image file | required |
| `--count` | `-n` | Number of dominant colors to extract (1–32) | `6` |
| `--json` | — | Output palette as JSON | `False` |

!!! note
    The option is `--count`, not `--colors`.

---

### `metrics`

Compare two images and report SSIM, PSNR, and MSE quality metrics.

**Syntax:**

```bash
pixopt metrics [ORIGINAL] [COMPARED] [OPTIONS]
```

**Examples:**

```bash
pixopt metrics photo.jpg photo_optimized.jpg
pixopt metrics photo.jpg photo_optimized.jpg --output json
```

**Command-specific options:**

| Option | Short | Description | Default |
| ------ | ----- | ----------- | ------- |
| `ORIGINAL` | — | Original image file | required |
| `COMPARED` | — | Image to compare against the original | required |
| `--output` | — | Report format: `table` or `json` | `table` |

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

### Complete asset bundle from a hero image

Generate all web assets from one source image:

```bash
pixopt bundle hero.jpg \
  --output-dir ./assets \
  --hero-width 1920 \
  --thumbnail-width 320 \
  --palette-n 8
```

### Add a watermark then optimize

Brand images before compression:

```bash
pixopt watermark photo.jpg photo_branded.jpg --text "(c) My Company" --position bottom-right --opacity 0.4
pixopt optimize photo_branded.jpg photo_final.jpg --quality 85 --width 1200
```

### PDF to images and back

Extract a PDF into PNGs and recombine selected pages:

```bash
pixopt pdf document.pdf -o ./pages --format png --dpi 200
pixopt pdf reduced.pdf --from-images ./pages/page_001.png ./pages/page_002.png -o reduced.pdf
```

### Find and review duplicates

Locate duplicates before cleaning up a media library:

```bash
pixopt duplicates ./media --recursive --threshold 5
pixopt duplicates ./media --recursive --threshold 0 --json > duplicates.json
```

### Choose the best format with benchmark

Before converting a large gallery, benchmark one representative image:

```bash
pixopt benchmark hero.jpg -q 80 -q 85 -q 90 -f webp -f avif
```

Then use the recommended format and quality for the full run.
