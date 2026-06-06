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
pixopt optimize photo.jpg photo_optimized.jpg --quality 80 --width 1200
pixopt optimize ./images ./optimized --recursive --quality 85 --format webp
```

### `batch`

Optimize multiple specific files at once.

```bash
pixopt batch photo1.jpg photo2.png photo3.bmp -o ./optimized --width 800
```

### `convert`

Convert an image to a different format or extension.

```bash
pixopt convert photo.png photo.webp -f webp
pixopt convert ./images ./webp_images -r -f webp
```

### `favicon`

Convert an image to a multi-resolution ICO favicon.

```bash
pixopt favicon logo.png favicon.ico
pixopt favicon logo.png --size 16 --size 32 --size 48
```

### `info`

Inspect image metadata without optimizing.

```bash
pixopt info photo.jpg
```

### `compare`

Generate an interactive HTML before/after slider.

```bash
pixopt compare photo.jpg comparison.html --open
```

### `srcset`

Generate responsive image variants and an HTML srcset snippet.

```bash
pixopt srcset hero.jpg --sizes 320,640,1024,1920 --output-dir ./responsive/
pixopt srcset hero.jpg --sizes 320,640,1024,1920 -f webp --html snippet.html
```

### `placeholder`

Extract a placeholder for lazy loading (color, LQIP, or blurhash).

```bash
pixopt placeholder photo.jpg --type color
pixopt placeholder photo.jpg --type lqip
pixopt placeholder photo.jpg --type blurhash -o blurhash.txt
```

## Use-case examples

### Lossless PNG/WEBP for UI assets

```bash
pixopt convert icon.png icon.webp --lossless -f webp
```

### Adaptive quality (target file size)

```bash
pixopt optimize photo.jpg --target-size 50
```

### Smart format detection

```bash
pixopt optimize photo.jpg --smart-format
pixopt convert graphic.png output --smart-format
```

### Backup originals before processing

```bash
pixopt optimize ./images --backup ./originals --recursive
```

### Skip already-optimized files

```bash
pixopt optimize ./images --min-size 10 --recursive
```

### Animated GIF to animated WEBP

```bash
pixopt convert animation.gif animation.webp -f webp
```

### Convert HEIC (iPhone) to JPEG

```bash
pixopt convert photo.heic photo.jpg
```

### Optimize SVG

```bash
pixopt convert icon.svg icon.min.svg
```
