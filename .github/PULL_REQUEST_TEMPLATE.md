# Pull Request

## Description

Briefly describe the changes in this pull request.

## Related Issue

Fixes #(issue number)

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring / code quality
- [ ] Breaking change

## Checklist

- [ ] I have read the [Contributing Guidelines](../CONTRIBUTING.md).
- [ ] I have run the full verification suite locally:
  - `ruff check .`
  - `ruff format . --check`
  - `mypy pixopt`
  - `python -m pyright`
  - `python -m bandit -r pixopt`
  - `python -m pip_audit .`
  - `pytest tests/ --cov=pixopt`
- [ ] I have added or updated tests where appropriate.
- [ ] I have updated the documentation if needed.
- [ ] My changes do not modify the intended behavior of the library.
