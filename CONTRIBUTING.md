# Contributing to pixopt

Thank you for your interest in contributing! This document will help you get started.

## Development setup

1. Fork and clone the repository:

   ```bash
   git clone https://github.com/MathiasPaulenko/pixopt.git
   cd pixopt
   ```

2. Create a virtual environment and install the package with development dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e ".[dev,docs]"
   ```

## Running tests

Run the full test suite with coverage:

```bash
pytest tests/ -v --cov=pixopt --cov-report=term-missing
```

## Code quality

All changes should pass the configured linting, type checking and formatting checks:

```bash
ruff check pixopt tests
ruff format pixopt tests
mypy pixopt
```

## Documentation

If your change affects public API or CLI behavior, please update the relevant
`docs/*.md` files and the `README.md` examples.

Build the documentation locally with:

```bash
mkdocs build --strict
```

## Commit style

We use [Conventional Commits](https://www.conventionalcommits.org/) to drive the
release workflow. Use prefixes such as `feat:`, `fix:`, `docs:`, `refactor:` or
`test:` in your commit messages.

## Pull request process

1. Fork the repository and create a feature branch.
2. Make your changes, adding or updating tests where appropriate.
3. Ensure `pytest`, `ruff check`, `mypy pixopt`, and `mkdocs build --strict` all pass.
4. Update the documentation and `CHANGELOG.md` if needed.
5. Submit a pull request with a clear description and link to any related issues.

By contributing, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).
