# Contributing

Thanks for your interest in contributing!

## Development setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/optimg.git
   cd optimg
   ```

2. Create a virtual environment and install dependencies:
   ```bash
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

## Pull requests

1. Fork the repository.
2. Create a feature branch.
3. Make your changes with tests.
4. Ensure `pytest` passes.
5. Submit a pull request with a clear description.
