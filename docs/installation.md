# Installation

pixopt requires **Python 3.10, 3.11, 3.12, 3.13, or 3.14**.

## From PyPI (recommended)

```bash
pip install pixopt
```

This installs the core package with Pillow, pillow-heif, Typer, Rich, piexif, and numpy.

## HEIC/HEIF support

HEIC/HEIF support is included out of the box because `pillow-heif` is a core dependency.

```bash
pip install pixopt
```

!!! note
    `pillow-heif` may require additional system libraries on Linux. See the [pillow-heif documentation](https://github.com/bigcat88/pillow_heif#installation) for platform-specific instructions.

## PDF support (optional)

For PDF import/export capabilities, install with the PDF extra:

```bash
pip install "pixopt[pdf]"
```

This installs [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`) for PDF processing.

## System dependencies

### macOS

No extra system dependencies are required. Homebrew users may optionally install:

```bash
brew install libheif  # For HEIC/HEIF support
```

### Linux (Debian/Ubuntu)

```bash
sudo apt-get install libheif-examples  # Optional, for HEIC/HEIF
```

### Windows

No extra system dependencies are required. HEIC/HEIF support works out of the box via `pillow-heif` wheels.

## From source

For development or bleeding-edge features:

```bash
git clone https://github.com/MathiasPaulenko/pixopt.git
cd pixopt
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Verify installation

```bash
pixopt --help
```

You should see the CLI help output with all available commands.

## Troubleshooting

### `ModuleNotFoundError: No module named 'pixopt'`

Make sure you are in the correct virtual environment and that the package was installed successfully:

```bash
pip list | grep pixopt
```

### HEIC/HEIF images fail to open

Install `pillow-heif` and ensure your Pillow version is 12.3.0 or newer:

```bash
pip install --upgrade Pillow pillow-heif
```

### Permission errors on Linux

If you see permission errors when installing, use `--user` or a virtual environment:

```bash
pip install --user pixopt
```
