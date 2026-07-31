# Agent Notes for pixopt

## Project Overview

`pixopt` is a Python library and CLI for image optimization. It is built with `hatchling` and supports Python 3.10–3.14. The codebase uses `Pillow>=12.3.0`, `pillow-heif`, `typer`, `rich`, `piexif`, and optionally `PyMuPDF` (fitz) for PDF support.

## Verification Commands

Run these from the repository root to check quality:

```powershell
ruff check .
ruff format .
mypy pixopt
python -m pyright
python -m bandit -r pixopt
python -m pip_audit .
pytest
python -m build
mkdocs build --strict
```

- `ruff check .` – lint all source and test files.
- `ruff format .` – auto-format code.
- `mypy pixopt` – type-check the package under strict mode.
- `python -m pyright` – additional type checking.
- `python -m bandit -r pixopt` – security linting.
- `python -m pip_audit .` – dependency vulnerability audit.
- `pytest` – run the full test suite.
- `python -m build` – build the package wheel/sdist.
- `mkdocs build --strict` – build the documentation.

## Environment Notes

- The default interpreter in this environment is Python 3.14.5.
- The test suite is designed to run on Python 3.10 through 3.14.
- `tests/test_pdf.py` is automatically skipped when `PyMuPDF` (`fitz`) is not installed.
- To run PDF tests, ensure `PyMuPDF` is installed for the target interpreter.

## Optional Dependencies

PDF support is now an optional extra. In `pyproject.toml`:

```toml
[project.optional-dependencies]
pdf = ["PyMuPDF>=1.23.0"]
```

## Key Architectural Conventions

- Image files are opened with context managers (`with Image.open(...) as ...`) and loaded before use to avoid keeping file handles open.
- Public APIs are type-hinted; mypy strict mode is enabled.
- Resource and security limits live in `pixopt._units` (input size, base64 length, PDF size/pages, image dimensions, srcset widths, etc.).
- `ProgressCallback` is a `Protocol` taking a single `ProgressInfo` argument.
- Preset merging uses `None` to mean "not provided"; booleans should use a tristate default when explicit flags must be distinguishable from defaults.
