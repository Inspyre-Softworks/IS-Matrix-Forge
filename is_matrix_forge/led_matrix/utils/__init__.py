"""
Utilities and helper functions for the LED matrix package.

This module restores convenient helpers removed from the package root to
prevent import-time hardware initialization. It provides lightweight,
optional routines such as first-run detection and safe controller access.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from platformdirs import PlatformDirs

log = logging.getLogger(__name__)

try:
    from .controller import LEDMatrixController, get_controllers  # noqa: F401
except ImportError:
    LEDMatrixController = None  # type: ignore

    def get_controllers(*_, **__):  # type: ignore
        raise RuntimeError('LEDMatrixController is unavailable')

try:
    from .display.text.scroller import scroll_text_on_multiple_matrices  # noqa: F401
except ImportError:
    def scroll_text_on_multiple_matrices(*_, **__):  # type: ignore
        raise RuntimeError('scroll_text_on_multiple_matrices is unavailable')


PLATFORM_DIRS = PlatformDirs('IS-Matrix-Forge', 'Inspyre Softworks')
APP_DIR: Path = PLATFORM_DIRS.user_data_path
MEMORY_FILE: Path = APP_DIR / 'memory.json'
MEMORY_FILE_TEMPLATE: dict[str, bool] = {'first_run': True}
first_run: bool = False

APP_DIR.mkdir(parents=True, exist_ok=True)
if not MEMORY_FILE.exists():
    MEMORY_FILE.write_text(json.dumps(MEMORY_FILE_TEMPLATE))


def _read_memory() -> dict:
    """Read the persistent state file safely."""
    try:
        with MEMORY_FILE.open('r') as fh:
            return json.load(fh)
    except Exception as exc:
        log.warning('Corrupted memory file: %s, resetting.', exc)
        _write_memory(MEMORY_FILE_TEMPLATE)
        return MEMORY_FILE_TEMPLATE.copy()


def _write_memory(memory: dict) -> None:
    """Write the persistent state file safely."""
    with MEMORY_FILE.open('w') as fh:
        json.dump(memory, fh)


def get_first_run() -> bool:
    """Return whether this is the first run of the application."""
    global first_run
    memory = _read_memory()
    first_run = memory.get('first_run', True)
    return first_run


def set_first_run(value: bool = False) -> None:
    """Mark the application as having completed its first run."""
    global first_run
    memory = _read_memory()
    memory['first_run'] = value
    _write_memory(memory)
    first_run = value


def process_first_run() -> None:
    """Display a welcome message on first run if controllers are available."""
    if not get_first_run():
        return

    try:
        controllers = get_controllers(threaded=True)
        scroll_text_on_multiple_matrices(controllers, 'Welcome!', threaded=True)
    except Exception as exc:
        log.warning('Failed to display first-run message: %s', exc)
    finally:
        set_first_run()


def initialize() -> None:
    """Run startup routines such as displaying the first-run welcome."""
    process_first_run()
    log.debug('Matrix helpers initialized (first_run=%s)', first_run)


__all__ = [
    'LEDMatrixController',
    'get_controllers',
    'scroll_text_on_multiple_matrices',
    'get_first_run',
    'set_first_run',
    'process_first_run',
    'initialize',
]

