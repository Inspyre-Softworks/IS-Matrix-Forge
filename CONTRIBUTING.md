# Contributing to IS Matrix Forge

Thank you for your interest in contributing! This document describes how to
get started and the conventions we follow.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Submitting Changes](#submitting-changes)
- [Controller Mixin Guidelines](#controller-mixin-guidelines)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating you agree to abide by its terms.

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/IS-Matrix-Forge.git
   cd IS-Matrix-Forge
   ```
3. **Create a branch** for your work:
   ```bash
   git checkout -b your-feature-or-fix
   ```

## Development Setup

This project uses [Poetry](https://python-poetry.org/) for dependency management.

```bash
# Install all dependencies (including dev)
poetry install

# Activate the virtual environment
poetry shell
```

## Running Tests

```bash
# Run the full test suite
pytest

# Or via Poetry
poetry run pytest
```

Tests live in the `tests/` directory. Hardware-dependent tests should be
skipped when the hardware is unavailable — use `pytest.mark.skip` or
`pytest.importorskip` as appropriate.

## Submitting Changes

1. Ensure all tests pass and no new linting errors are introduced.
2. Commit your changes with a clear, concise message.
3. Push your branch and open a Pull Request against the default branch.
4. Fill in the pull request template describing your changes.

## Controller Mixin Guidelines

When adding new controller functionality, see
[`docs/contributing-mixins.md`](docs/contributing-mixins.md) for a full
guide on cooperative initialization and the `@synchronized` decorator.

Quick checklist for a new mixin:

- Create `is_matrix_forge/led_matrix/controller/components/<name>.py` with a
  `ClassNameManager` class.
- Accept keyword-only args in `__init__` and call `super().__init__(**kwargs)`.
- Avoid heavy IO in `__init__`; use `@synchronized` for device-touching methods.
- If calling synchronized methods in `__init__`, ensure MRO places you after
  `BreatherManager`.
- Add docstrings, type hints, and at least one test.
- Per-LED brightness changes must stage and commit a complete framebuffer
  atomically; never update cache or history before the commit succeeds.
- Update every relevant README, user-manual, getting-started, changelog, and
  architecture document when adding public controller capabilities.
