"""Tests for led-matrix CLI argument parsing.

These tests exercise the ``Arguments`` class (and the individual
``register_command`` helpers) without touching any hardware.  They verify:

* All expected subcommands are registered.
* ``-L`` / ``-R`` matrix-selection flags work whether placed **before** or
  **after** the subcommand name.
* Default values are correct.
* The ``set-presets-dir`` subcommand captures its positional argument.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest


# ---------------------------------------------------------------------------
# Stub heavy optional dependencies so the argument module can be imported
# without installing the full dependency tree.
# ---------------------------------------------------------------------------

def _install_test_stubs() -> None:
    """Provide lightweight stand-ins for optional runtime dependencies."""

    if 'is_matrix_forge.led_matrix.controller.controller' not in sys.modules:
        ctrl_mod = ModuleType('is_matrix_forge.led_matrix.controller.controller')

        class LEDMatrixController:  # pragma: no cover
            pass

        ctrl_mod.LEDMatrixController = LEDMatrixController
        sys.modules['is_matrix_forge.led_matrix.controller.controller'] = ctrl_mod

    if 'is_matrix_forge.led_matrix.helpers.device' not in sys.modules:
        dev_mod = ModuleType('is_matrix_forge.led_matrix.helpers.device')
        dev_mod.DEVICES = []
        dev_mod.get_devices = lambda *args, **kwargs: []
        sys.modules['is_matrix_forge.led_matrix.helpers.device'] = dev_mod

    stubs = {
        'is_matrix_forge.common.dirs': {
            'APP_DIRS': type('_D', (), {'user_data_path': Path('/tmp/led-matrix')})(),
            'APP_DIR':  Path('/tmp/led-matrix'),
            'PRESETS_DIR': Path('/tmp/led-matrix/presets'),
        },
        'is_matrix_forge.led_matrix.constants': {
            'APP_DIRS': type('_D', (), {'user_data_path': Path('/tmp/led-matrix')})(),
            'SLOT_MAP': {},
        },
        'is_matrix_forge.common.helpers.github_api': {
            'REPO_PRESETS_URL': 'https://example.com/presets',
            'assemble_github_content_path_url': lambda *a, **kw: '',
        },
    }

    for mod_name, attrs in stubs.items():
        if mod_name not in sys.modules:
            m = ModuleType(mod_name)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[mod_name] = m


_install_test_stubs()

from is_matrix_forge.led_matrix.Scripts.led_matrix.arguments import Arguments  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(argv: list[str]):
    """Build a fresh Arguments instance and parse *argv* without touching sys.argv."""
    args = Arguments()
    return args.parse_args(argv)


# ---------------------------------------------------------------------------
# Subcommand registration
# ---------------------------------------------------------------------------

EXPECTED_SUBCOMMANDS = [
    'scroll-text',
    'display-text',
    'identify-matrices',
    'bootloader',
    'install-presets',
    'scroll-until',
    'set-presets-dir',
]


@pytest.mark.parametrize('subcommand', EXPECTED_SUBCOMMANDS)
def test_subcommand_registered(subcommand):
    """Every expected subcommand must appear in the parser's choices."""
    args = Arguments()
    choices = args.SUBCOMMANDS.choices
    assert subcommand in choices, f'Subcommand {subcommand!r} not found in {list(choices)}'


# ---------------------------------------------------------------------------
# -L / -R before the subcommand name (classic position)
# ---------------------------------------------------------------------------

class TestMatrixSelectionBeforeSubcommand:
    def test_only_left_before_scroll_text(self):
        ns = _parse(['-L', 'scroll-text', 'hello'])
        assert ns.only_left is True
        assert ns.only_right is False

    def test_only_right_before_scroll_text(self):
        ns = _parse(['-R', 'scroll-text', 'hello'])
        assert ns.only_right is True
        assert ns.only_left is False

    def test_only_left_before_display_text(self):
        ns = _parse(['-L', 'display-text', 'hello'])
        assert ns.only_left is True

    def test_only_right_before_identify(self):
        ns = _parse(['-R', 'identify-matrices'])
        assert ns.only_right is True

    def test_only_right_before_bootloader(self):
        ns = _parse(['-R', 'bootloader'])
        assert ns.only_right is True


# ---------------------------------------------------------------------------
# -L / -R after the subcommand name (the previously broken position)
# ---------------------------------------------------------------------------

class TestMatrixSelectionAfterSubcommand:
    def test_only_left_after_scroll_text(self):
        ns = _parse(['scroll-text', '-L', 'hello'])
        assert ns.only_left is True
        assert ns.only_right is False

    def test_only_right_after_scroll_text(self):
        ns = _parse(['scroll-text', '-R', 'hello'])
        assert ns.only_right is True
        assert ns.only_left is False

    def test_only_left_after_display_text(self):
        ns = _parse(['display-text', '-L', 'hello'])
        assert ns.only_left is True

    def test_only_right_after_display_text(self):
        ns = _parse(['display-text', '-R', 'hello'])
        assert ns.only_right is True

    def test_only_left_after_identify(self):
        ns = _parse(['identify-matrices', '-L'])
        assert ns.only_left is True

    def test_only_right_after_bootloader(self):
        ns = _parse(['bootloader', '-R'])
        assert ns.only_right is True

    def test_only_left_after_scroll_until(self):
        ns = _parse(['scroll-until', '-L', 'Loading…', 'sleep 1'])
        assert ns.only_left is True


# ---------------------------------------------------------------------------
# Default values (no -L / -R)
# ---------------------------------------------------------------------------

class TestMatrixSelectionDefaults:
    def test_both_false_when_no_flag(self):
        ns = _parse(['scroll-text', 'hello'])
        assert ns.only_left is False
        assert ns.only_right is False


# ---------------------------------------------------------------------------
# scroll-text arguments
# ---------------------------------------------------------------------------

class TestScrollTextArgs:
    def test_positional_input(self):
        ns = _parse(['scroll-text', 'Hello World'])
        assert ns.input == 'Hello World'

    def test_default_direction(self):
        ns = _parse(['scroll-text', 'hi'])
        assert ns.direction == 'up'

    def test_custom_direction(self):
        ns = _parse(['scroll-text', '-d', 'h', 'hi'])
        assert ns.direction == 'h'

    def test_sequential_flag(self):
        ns = _parse(['scroll-text', '--sequential', 'hi'])
        assert ns.sequential is True


# ---------------------------------------------------------------------------
# display-text arguments
# ---------------------------------------------------------------------------

class TestDisplayTextArgs:
    def test_positional_text(self):
        ns = _parse(['display-text', 'Status: OK'])
        assert ns.text == 'Status: OK'

    def test_default_run_for_is_none(self):
        ns = _parse(['display-text', 'hi'])
        assert ns.run_for is None

    def test_run_for_accepts_float(self):
        ns = _parse(['display-text', '--run-for', '3.5', 'hi'])
        assert ns.run_for == pytest.approx(3.5)

    def test_skip_clear_default(self):
        ns = _parse(['display-text', 'hi'])
        assert ns.skip_clear is False


# ---------------------------------------------------------------------------
# identify-matrices arguments
# ---------------------------------------------------------------------------

class TestIdentifyMatricesArgs:
    def test_default_cycle_count(self):
        from is_matrix_forge.led_matrix.Scripts.identify_matrices import DEFAULT_CYCLES
        ns = _parse(['identify-matrices'])
        assert ns.cycle_count == DEFAULT_CYCLES

    def test_custom_runtime(self):
        ns = _parse(['identify-matrices', '-t', '10'])
        assert float(ns.runtime) == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# scroll-until arguments
# ---------------------------------------------------------------------------

class TestScrollUntilArgs:
    def test_positional_args(self):
        ns = _parse(['scroll-until', 'Building…', 'make all'])
        assert ns.input == 'Building…'
        assert ns.command == 'make all'

    def test_default_on_complete(self):
        ns = _parse(['scroll-until', 'wait', 'sleep 1'])
        assert ns.on_complete == 'clear'

    def test_on_complete_leave(self):
        ns = _parse(['scroll-until', '--on-complete', 'leave', 'wait', 'sleep 1'])
        assert ns.on_complete == 'leave'

    def test_on_complete_fade(self):
        ns = _parse(['scroll-until', '--on-complete', 'fade', 'wait', 'sleep 1'])
        assert ns.on_complete == 'fade'


# ---------------------------------------------------------------------------
# set-presets-dir arguments
# ---------------------------------------------------------------------------

class TestSetPresetsDirArgs:
    def test_path_captured(self):
        ns = _parse(['set-presets-dir', '/custom/presets'])
        assert ns.path == '/custom/presets'
