# CLI Usage

The CLI is built with [Typer](https://typer.tiangolo.com/) and provides an intuitive interface for all optimization features.

## Global options

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

## Commands

### `optimize`

Optimize a single image or all images in a directory.

```bash
optimg optimize photo.jpg photo_optimized.jpg --quality 80 --width 1200
optimg optimize ./images ./optimized --recursive --quality 85 --format webp
```

### `batch`

Optimize multiple specific files at once.

```bash
optimg batch photo1.jpg photo2.png photo3.bmp -o ./optimized --width 800
```

### `convert`

Convert an image to a different format or extension.

```bash
optimg convert photo.png photo.webp -f webp
optimg convert ./images ./webp_images -r -f webp
```

### `favicon`

Convert an image to a multi-resolution ICO favicon.

```bash
optimg favicon logo.png favicon.ico
optimg favicon logo.png --size 16 --size 32 --size 48
```

### `info`

Inspect image metadata without optimizing.

```bash
optimg info photo.jpg
```

### `compare`

Generate an interactive HTML before/after slider.

```bash
optimg compare photo.jpg comparison.html --open
```

### `srcset`

Generate responsive image variants and an HTML srcset snippet.

```bash
optimg srcset hero.jpg --sizes 320,640,1024,1920 --output-dir ./responsive/
optimg srcset hero.jpg --sizes 320,640,1024,1920 -f webp --html snippet.html
```

### `placeholder`

Extract a placeholder for lazy loading (color, LQIP, or blurhash).

```bash
optimg placeholder photo.jpg --type color
optimg placeholder photo.jpg --type lqip
optimg placeholder photo.jpg --type blurhash -o blurhash.txt
```

## Use-case examples

### Lossless PNG/WEBP for UI assets

```bash
optimg convert icon.png icon.webp --lossless -f webp
```

### Adaptive quality (target file size)

```bash
optimg optimize photo.jpg --target-size 50
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

### Animated GIF to animated WEBP

```bash
optimg convert animation.gif animation.webp -f webp
```

### Convert HEIC (iPhone) to JPEG

```bash
optimg convert photo.heic photo.jpg
```

### Optimize SVG

```bash
optimg convert icon.svg icon.min.svg
```
