"""Tests for PresetConfig: directory tracking, file migration, and presence checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


# ---------------------------------------------------------------------------
# Stub heavy optional dependencies before any is_matrix_forge import.
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

    if 'is_matrix_forge.common.dirs' not in sys.modules:
        dirs_mod = ModuleType('is_matrix_forge.common.dirs')
        dirs_mod.APP_DIRS = type('_D', (), {'user_data_path': Path('/tmp/led-matrix')})()
        dirs_mod.APP_DIR  = dirs_mod.APP_DIRS.user_data_path
        dirs_mod.PRESETS_DIR = dirs_mod.APP_DIR / 'presets'
        sys.modules['is_matrix_forge.common.dirs'] = dirs_mod


_install_test_stubs()

from is_matrix_forge.common.preset_config import (  # noqa: E402
    PresetConfig,
    _move_preset_files,
    SETTINGS_FILE_NAME,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _touch_preset(directory: Path, name: str = 'test.json') -> Path:
    """Create a minimal JSON preset file and return its path."""
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    p.write_text(json.dumps({'test': True}))
    return p


# ---------------------------------------------------------------------------
# PresetConfig – basic property behaviour
# ---------------------------------------------------------------------------

class TestPresetConfigDefaults:
    def test_default_presets_dir(self, tmp_path):
        config = PresetConfig(tmp_path)
        assert config.presets_dir == tmp_path / 'presets'

    def test_settings_file_path(self, tmp_path):
        config = PresetConfig(tmp_path)
        assert config._settings_file == tmp_path / SETTINGS_FILE_NAME

    def test_has_presets_returns_false_when_empty(self, tmp_path):
        config = PresetConfig(tmp_path)
        assert config.has_presets() is False

    def test_has_presets_returns_true_when_json_present(self, tmp_path):
        config = PresetConfig(tmp_path)
        _touch_preset(config.presets_dir)
        assert config.has_presets() is True

    def test_has_presets_ignores_non_json_files(self, tmp_path):
        config = PresetConfig(tmp_path)
        config.presets_dir.mkdir(parents=True, exist_ok=True)
        (config.presets_dir / 'readme.txt').write_text('hello')
        assert config.has_presets() is False


# ---------------------------------------------------------------------------
# PresetConfig – loading from an existing settings file
# ---------------------------------------------------------------------------

class TestPresetConfigLoad:
    def test_loads_presets_dir_from_settings(self, tmp_path):
        custom_dir = tmp_path / 'custom' / 'presets'
        _write_json(
            tmp_path / SETTINGS_FILE_NAME,
            {'presets_dir': str(custom_dir)},
        )
        config = PresetConfig(tmp_path)
        assert config.presets_dir == custom_dir

    def test_falls_back_to_default_on_missing_settings(self, tmp_path):
        config = PresetConfig(tmp_path)
        assert config.presets_dir == tmp_path / 'presets'

    def test_falls_back_to_default_on_corrupt_settings(self, tmp_path):
        (tmp_path / SETTINGS_FILE_NAME).write_text('NOT JSON }{')
        config = PresetConfig(tmp_path)
        assert config.presets_dir == tmp_path / 'presets'


# ---------------------------------------------------------------------------
# PresetConfig – setter: moves files and persists setting
# ---------------------------------------------------------------------------

class TestPresetConfigSetter:
    def test_setter_persists_new_path(self, tmp_path):
        config = PresetConfig(tmp_path)
        new_dir = tmp_path / 'elsewhere' / 'presets'
        config.presets_dir = new_dir
        assert config.presets_dir == new_dir
        saved = json.loads((tmp_path / SETTINGS_FILE_NAME).read_text())
        assert saved['presets_dir'] == str(new_dir)

    def test_setter_moves_existing_json_files(self, tmp_path):
        config = PresetConfig(tmp_path)
        old_dir = config.presets_dir
        _touch_preset(old_dir, 'a.json')
        _touch_preset(old_dir, 'b.json')

        new_dir = tmp_path / 'new_presets'
        config.presets_dir = new_dir

        assert (new_dir / 'a.json').exists()
        assert (new_dir / 'b.json').exists()
        # originals are gone
        assert not (old_dir / 'a.json').exists()
        assert not (old_dir / 'b.json').exists()

    def test_setter_noop_when_path_unchanged(self, tmp_path):
        config = PresetConfig(tmp_path)
        original = config.presets_dir
        config.presets_dir = original  # no-op
        # settings file should not be created for a no-op
        assert not (tmp_path / SETTINGS_FILE_NAME).exists()

    def test_setter_does_not_move_nonexistent_old_dir(self, tmp_path):
        config = PresetConfig(tmp_path)
        new_dir = tmp_path / 'new_presets'
        # old dir does not exist – should not raise
        config.presets_dir = new_dir
        assert config.presets_dir == new_dir


# ---------------------------------------------------------------------------
# PresetConfig – reconcile
# ---------------------------------------------------------------------------

class TestPresetConfigReconcile:
    def test_reconcile_moves_files_from_default_to_configured(self, tmp_path):
        """If settings point at a custom dir but files live at default, move them."""
        default_presets = tmp_path / 'presets'
        _touch_preset(default_presets, 'c.json')

        custom_presets = tmp_path / 'custom_presets'
        _write_json(
            tmp_path / SETTINGS_FILE_NAME,
            {'presets_dir': str(custom_presets)},
        )

        config = PresetConfig(tmp_path)
        config.reconcile()

        assert (custom_presets / 'c.json').exists()
        assert not (default_presets / 'c.json').exists()

    def test_reconcile_noop_when_desired_already_has_files(self, tmp_path):
        """No move should happen when the configured directory already has presets."""
        custom_presets = tmp_path / 'custom_presets'
        _touch_preset(custom_presets, 'd.json')

        # Also seed the default dir to ensure it is NOT touched.
        default_presets = tmp_path / 'presets'
        _touch_preset(default_presets, 'd_old.json')

        _write_json(
            tmp_path / SETTINGS_FILE_NAME,
            {'presets_dir': str(custom_presets)},
        )

        config = PresetConfig(tmp_path)
        config.reconcile()

        # custom has its file; default still has its file (untouched).
        assert (custom_presets / 'd.json').exists()
        assert (default_presets / 'd_old.json').exists()

    def test_reconcile_noop_when_configured_equals_default(self, tmp_path):
        """When configured dir == default dir, reconcile is a no-op."""
        config = PresetConfig(tmp_path)
        _touch_preset(config.presets_dir, 'e.json')
        config.reconcile()
        assert (config.presets_dir / 'e.json').exists()


# ---------------------------------------------------------------------------
# _move_preset_files helper
# ---------------------------------------------------------------------------

class TestMovePresetFiles:
    def test_moves_json_files(self, tmp_path):
        src = tmp_path / 'src'
        dst = tmp_path / 'dst'
        _touch_preset(src, 'x.json')
        _touch_preset(src, 'y.json')
        _move_preset_files(src, dst)
        assert (dst / 'x.json').exists()
        assert (dst / 'y.json').exists()

    def test_creates_destination_if_missing(self, tmp_path):
        src = tmp_path / 'src'
        dst = tmp_path / 'deep' / 'nested' / 'dst'
        _touch_preset(src, 'z.json')
        _move_preset_files(src, dst)
        assert (dst / 'z.json').exists()

    def test_ignores_non_json_files(self, tmp_path):
        src = tmp_path / 'src'
        dst = tmp_path / 'dst'
        src.mkdir()
        (src / 'readme.txt').write_text('hi')
        _move_preset_files(src, dst)
        assert not (dst / 'readme.txt').exists()


# ---------------------------------------------------------------------------
# ensure_dir
# ---------------------------------------------------------------------------

class TestEnsureDir:
    def test_creates_presets_dir(self, tmp_path):
        config = PresetConfig(tmp_path)
        assert not config.presets_dir.exists()
        config.ensure_dir()
        assert config.presets_dir.is_dir()
