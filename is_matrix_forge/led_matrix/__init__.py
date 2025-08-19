"""Utilities and helper functions for the LED matrix package.

This module exposes a handful of convenience helpers that historically lived
in the package ``__init__`` module.  The previous refactor removed them to
avoid expensive side effects on import which meant downstream consumers lost
easy access to the helpers.  The helpers are restored here but are kept
lazy/optional so that importing this module continues to work in lightweight
environments (e.g. unit tests without hardware present).
"""

from __future__ import annotations

import json
from platformdirs import PlatformDirs

try:  # pragma: no cover - optional dependency
    from .controller import LEDMatrixController, get_controllers  # noqa: F401
except ImportError:  # pragma: no cover
    LEDMatrixController = None  # type: ignore

    def get_controllers(*args, **kwargs):  # type: ignore
        raise RuntimeError("LEDMatrixController is unavailable")

try:  # pragma: no cover - optional dependency
    from .display.text.scroller import scroll_text_on_multiple_matrices  # noqa: F401
except ImportError:  # pragma: no cover
    def scroll_text_on_multiple_matrices(*args, **kwargs):  # type: ignore
        raise RuntimeError("scroll_text_on_multiple_matrices is unavailable")

PLATFORM_DIRS = PlatformDirs("IS-Matrix-Forge", "Inspyre Softworks")
APP_DIR = PLATFORM_DIRS.user_data_path
MEMORY_FILE = APP_DIR / "memory.ini"
MEMORY_FILE_TEMPLATE = {"first_run": True}
first_run = False

APP_DIR.mkdir(parents=True, exist_ok=True)
if not MEMORY_FILE.exists():
    MEMORY_FILE.write_text(json.dumps(MEMORY_FILE_TEMPLATE))


def _read_memory() -> dict:
    with open(MEMORY_FILE, "r") as fh:
        return json.load(fh)


def _write_memory(memory: dict) -> None:
    with open(MEMORY_FILE, "w") as fh:
        json.dump(memory, fh)


def get_first_run() -> bool:
    """Return whether this is the first run of the application."""

    global first_run
    memory = _read_memory()
    first_run = memory["first_run"]
    return first_run


def set_first_run(value: bool = False) -> None:
    """Mark the application as having completed its first run."""

    global first_run
    memory = _read_memory()
    memory["first_run"] = value
    _write_memory(memory)
    first_run = value


def process_first_run() -> None:
    """Display a welcome message on first run if controllers are available."""

    if get_first_run():
        controllers = get_controllers(threaded=True)
        scroll_text_on_multiple_matrices(
            controllers, "Welcome!", threaded=True
        )
        set_first_run()


def initialize() -> None:
    """Run startup routines such as displaying the first-run welcome."""

    process_first_run()


__all__ = [
    "LEDMatrixController",
    "get_controllers",
    "scroll_text_on_multiple_matrices",
    "get_first_run",
    "set_first_run",
    "process_first_run",
    "initialize",
]

