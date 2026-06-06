# Contributing

Thank you for your interest in contributing to **pixopt**! We welcome bug reports, feature requests, documentation improvements, and code contributions.

---

## Quick setup

1. Fork the repository on GitHub.
2. Clone your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/pixopt.git
cd pixopt
```

3. Create a virtual environment and install in development mode:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

!!! tip
    The `[dev]` extra installs all development dependencies: pytest, ruff, mypy, python-semantic-release, pytest-cov.

---

## Development workflow

### 1. Create a branch

```bash
git checkout -b feature/my-new-feature
```

### 2. Make your changes

- Write clean, typed Python code.
- Add docstrings to public functions and classes.
- Update documentation if you change user-facing behavior.

### 3. Run tests and linters

Before submitting, ensure everything passes:

```bash
# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=src/pixopt --cov-report=term-missing

# Run linter
ruff check src tests

# Run type checker
mypy src
```

### 4. Commit your changes

We use **Conventional Commits** to drive our automated semantic versioning. Please follow this format:

| Prefix | Use when... | Version bump |
|--------|-------------|--------------|
| `feat:` | Adding a new feature | MINOR |
| `fix:` | Fixing a bug | PATCH |
| `docs:` | Documentation-only changes | None |
| `style:` | Code style changes (formatting, semicolons, etc.) | None |
| `refactor:` | Code refactoring without behavior change | None |
| `test:` | Adding or updating tests | None |
| `chore:` | Maintenance tasks (build, CI, dependencies) | None |
| `BREAKING CHANGE:` | Any breaking API change | MAJOR |

**Examples:**

```bash
git commit -m "feat: add AVIF format support"
git commit -m "fix: resolve HEIC conversion error on Windows"
git commit -m "docs: update CLI usage examples"
git commit -m "refactor: simplify adaptive quality algorithm"
```

!!! warning
    Commits that do not follow Conventional Commits will not trigger a version bump, but they are still welcome for documentation and internal improvements.

### 5. Push and open a Pull Request

```bash
git push origin feature/my-new-feature
```

Then open a Pull Request on GitHub against the `main` branch. Fill out the PR template and link any related issues.

---

## Code style

- **PEP 8** compliance (enforced by `ruff`).
- **Type hints** on all public functions and methods.
- **Google-style docstrings** for public APIs (used by mkdocstrings).
- **F-strings** over `.format()` or `%` formatting.
- **Pathlib** over `os.path` for file operations.

---

## Reporting bugs

When reporting a bug, please include:

1. Your operating system and Python version.
2. The exact command or code that triggers the issue.
3. The full error message and traceback.
4. A minimal example image or file that reproduces the problem (if applicable).

Open an issue at [GitHub Issues](https://github.com/MathiasPaulenko/pixopt/issues).

---

## Requesting features

Feature requests are welcome! Open an issue and describe:

- What problem you are trying to solve.
- How you would like the feature to work.
- Any alternative solutions you have considered.

---

## License

By contributing to pixopt, you agree that your contributions will be licensed under the [MIT License](https://github.com/MathiasPaulenko/pixopt/blob/main/LICENSE).
