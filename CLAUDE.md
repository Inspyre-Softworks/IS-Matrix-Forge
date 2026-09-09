# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IS Matrix Forge is a Python framework (3.12+) for driving 9×34 LED matrix displays over serial (pyserial). Hardware identifiers: VID 0x32AC, PID 0x20, serial-number prefix FRAK. Tests must pass without hardware attached — hardware-dependent tests should be skipped when the device is unavailable.

## Commands

Poetry manages dependencies and the build:

```bash
poetry install                      # install all deps (incl. dev)
poetry run pytest                   # run full test suite
poetry run pytest tests/test_grid.py                  # single test file
poetry run pytest tests/test_grid.py::test_name       # single test
ruff check .                        # lint (matches CI; config in [tool.ruff]; ruff is not a dev dep — pip install ruff)
```

The suite includes `tests/test_import_smoke.py`, which imports every module in
the package in a clean subprocess — a broken import anywhere fails the suite.
`ruff check .` passes with zero violations; keep it that way.

Pytest config lives in `pyproject.toml` (`testpaths = ["tests"]`, `test_*.py` / `Test*` / `test_*`). `tests/conftest.py` adds the repo root to `sys.path`, so tests run against the source tree without installing the package.

Entry-point scripts (from `[tool.poetry.scripts]`): `led-matrix`, `pixel-grid` (both under `is_matrix_forge/led_matrix/scripts/`).

## Architecture

### Controller mixin composition (the core design)

`LEDMatrixController` (`is_matrix_forge/led_matrix/controller/controller.py`) composes functionality through multiple inheritance with **cooperative initialization** — every mixin accepts keyword-only args and calls `super().__init__(**kwargs)` in a single chain. See ADR at `docs/adr/0001-controller-mro-and-cooperative-init.md` and `docs/contributing-mixins.md`.

Current MRO (init order, enforced by `tests/test_controller_mro.py`):

```
DeviceBase → DisplayHistoryManager → KeepAliveManager → GameManager →
AnimationManager → DrawingManager → BrightnessManager → BreatherManager →
IdentifyManager → Loggable
```

Ordering constraints that must be preserved:
- `DeviceBase` first so `self.device` exists for all downstream mixins.
- `BrightnessManager` before `BreatherManager` — the breather reads brightness at init.
- `BrightnessManager` owns the known 9×34 raw grayscale framebuffer. Complete
  writes establish state; partial pixel writes fail closed when state is unknown.
- `AnimationManager` loads named JSON animations from its configurable
  platform-specific `animations_dir`.
- `BreatherManager` before `IdentifyManager` — `IdentifyManager.__init__` may call `@synchronized` methods that rely on the breather pause context.
- `Loggable` last so `parent_log_device=` can pass through the chain without kwarg collisions.

Thread safety: pass `thread_safe=True` to enable an internal `RLock`; the `@synchronized` decorator guards device-touching methods and expects the breather pause context to exist.

### Adding a new controller mixin

1. Create `is_matrix_forge/led_matrix/controller/components/<name>.py` with a `<Name>Manager` class (reference: `components/example_template.py`).
2. Keyword-only `__init__` args; call `super().__init__(**kwargs)`; no heavy IO in `__init__`.
3. Use `@synchronized` for hardware-touching methods. If you call synchronized methods in `__init__`, the mixin must come after `BreatherManager` in the MRO.
4. Insert into `LEDMatrixController`'s base list after `DeviceBase` and before `IdentifyManager`; update `tests/test_controller_mro.py`'s expected order.

### Package layout (high level)

- `is_matrix_forge/led_matrix/` — core: `controller/` (mixins in `components/`), `display/` (animations, grid, text, effects, scenes), `commands/` (low-level serial commands), `helpers/` (device discovery; `helpers.device.DEVICES` is resolved lazily — no serial scan at import time), `scripts/` (CLI entry points), `hardware.py`, `constants.py`, `errors/` (all exceptions inherit `LEDMatrixControllerError`).
- `is_matrix_forge/designer_gui/` — PySimpleGUI-based matrix designer (reachable via `pixel-grid`).
- `is_matrix_forge/progress.py` — tqdm-style progress bar rendered on the matrix.
- `is_matrix_forge/log_engine.py` — InspyLogger integration with a fallback `Loggable` stub (both accept `parent_log_device=`); also home of `log_on_exception`. Use these loggers in library code, not `print()`.
- `presets/` — bundled patterns/animations (packaged via sdist includes).
- `docs/` — Sphinx docs (Read the Docs via `.readthedocs.yaml`), ADRs, user manual.
