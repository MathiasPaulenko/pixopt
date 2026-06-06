# Contributing

Thanks for your interest in contributing!

See [CONTRIBUTING.md](https://github.com/yourusername/optimg/blob/main/CONTRIBUTING.md) for the full guide.

## Quick setup

```bash
git clone https://github.com/yourusername/optimg.git
cd optimg
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest tests/ -v
```

## Code style

- Follow PEP 8.
- Use type hints where possible.
- Keep docstrings concise and descriptive.
