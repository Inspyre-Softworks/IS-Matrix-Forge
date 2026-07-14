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
    _load_manifest_filenames,
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


def _create_manifest(directory: Path, *filenames: str) -> Path:
    """Write a ``manifest.json`` that lists *filenames* as tracked presets."""
    directory.mkdir(parents=True, exist_ok=True)
    manifest_data = {
        'meta': {'version': 'dev', 'date': '2024-01-01T00:00:00'},
        'manifest': [{name: 'test_checksum'} for name in filenames],
    }
    p = directory / 'manifest.json'
    p.write_text(json.dumps(manifest_data))
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
        _create_manifest(old_dir, 'a.json', 'b.json')

        new_dir = tmp_path / 'new_presets'
        config.presets_dir = new_dir

        assert (new_dir / 'a.json').exists()
        assert (new_dir / 'b.json').exists()
        # originals are gone
        assert not (old_dir / 'a.json').exists()
        assert not (old_dir / 'b.json').exists()

    def test_setter_removes_old_dir_when_empty(self, tmp_path):
        """Old directory is removed once all manifest-tracked files are moved."""
        config = PresetConfig(tmp_path)
        old_dir = config.presets_dir
        _touch_preset(old_dir, 'c.json')
        _create_manifest(old_dir, 'c.json')

        new_dir = tmp_path / 'new_presets'
        config.presets_dir = new_dir

        assert not old_dir.exists()

    def test_setter_keeps_old_dir_when_user_files_remain(self, tmp_path):
        """Old directory is kept when the user has files not in the manifest."""
        config = PresetConfig(tmp_path)
        old_dir = config.presets_dir
        _touch_preset(old_dir, 'managed.json')
        _create_manifest(old_dir, 'managed.json')
        # user file NOT in manifest
        user_file = old_dir / 'my_custom.json'
        user_file.write_text(json.dumps({'custom': True}))

        new_dir = tmp_path / 'new_presets'
        config.presets_dir = new_dir

        # managed preset was moved
        assert (new_dir / 'managed.json').exists()
        # user file was left untouched
        assert user_file.exists()
        # source directory still present because user file remains
        assert old_dir.is_dir()

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
        _create_manifest(default_presets, 'c.json')

        custom_presets = tmp_path / 'custom_presets'
        _write_json(
            tmp_path / SETTINGS_FILE_NAME,
            {'presets_dir': str(custom_presets)},
        )

        config = PresetConfig(tmp_path)
        config.reconcile()

        assert (custom_presets / 'c.json').exists()
        assert not (default_presets / 'c.json').exists()

    def test_reconcile_removes_default_dir_when_empty(self, tmp_path):
        """Default directory is removed after reconcile when no user files remain."""
        default_presets = tmp_path / 'presets'
        _touch_preset(default_presets, 'c.json')
        _create_manifest(default_presets, 'c.json')

        custom_presets = tmp_path / 'custom_presets'
        _write_json(
            tmp_path / SETTINGS_FILE_NAME,
            {'presets_dir': str(custom_presets)},
        )

        config = PresetConfig(tmp_path)
        config.reconcile()

        assert not default_presets.exists()

    def test_reconcile_keeps_default_dir_when_user_files_remain(self, tmp_path):
        """Default directory is kept when user files not in the manifest exist there."""
        default_presets = tmp_path / 'presets'
        _touch_preset(default_presets, 'c.json')
        _create_manifest(default_presets, 'c.json')
        # user file NOT in manifest
        user_file = default_presets / 'my_preset.json'
        user_file.write_text(json.dumps({'user': True}))

        custom_presets = tmp_path / 'custom_presets'
        _write_json(
            tmp_path / SETTINGS_FILE_NAME,
            {'presets_dir': str(custom_presets)},
        )

        config = PresetConfig(tmp_path)
        config.reconcile()

        # managed file was moved
        assert (custom_presets / 'c.json').exists()
        # user file was not moved or deleted
        assert user_file.exists()
        # default dir still exists because user file remains
        assert default_presets.is_dir()

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
    def test_moves_manifest_tracked_files(self, tmp_path):
        src = tmp_path / 'src'
        dst = tmp_path / 'dst'
        _touch_preset(src, 'x.json')
        _touch_preset(src, 'y.json')
        _create_manifest(src, 'x.json', 'y.json')
        _move_preset_files(src, dst)
        assert (dst / 'x.json').exists()
        assert (dst / 'y.json').exists()
        # manifest.json itself must also travel to the destination
        assert (dst / 'manifest.json').exists()

    def test_does_not_move_files_not_in_manifest(self, tmp_path):
        src = tmp_path / 'src'
        dst = tmp_path / 'dst'
        _touch_preset(src, 'tracked.json')
        _create_manifest(src, 'tracked.json')
        # user file — NOT in manifest
        user_file = src / 'user_custom.json'
        user_file.write_text('{}')

        _move_preset_files(src, dst)

        assert (dst / 'tracked.json').exists()
        assert not (dst / 'user_custom.json').exists()
        assert user_file.exists(), 'user file must be left untouched'

    def test_returns_true_when_src_empty_after_move(self, tmp_path):
        src = tmp_path / 'src'
        dst = tmp_path / 'dst'
        _touch_preset(src, 'only.json')
        _create_manifest(src, 'only.json')

        src_empty = _move_preset_files(src, dst)

        assert src_empty is True

    def test_returns_false_when_user_files_remain(self, tmp_path):
        src = tmp_path / 'src'
        dst = tmp_path / 'dst'
        _touch_preset(src, 'managed.json')
        _create_manifest(src, 'managed.json')
        (src / 'user.json').write_text('{}')

        src_empty = _move_preset_files(src, dst)

        assert src_empty is False

    def test_no_manifest_moves_nothing(self, tmp_path):
        """When no manifest exists, _move_preset_files must not touch any file."""
        src = tmp_path / 'src'
        dst = tmp_path / 'dst'
        _touch_preset(src, 'mystery.json')

        _move_preset_files(src, dst)

        assert not (dst / 'mystery.json').exists()
        assert (src / 'mystery.json').exists()

    def test_creates_destination_if_missing(self, tmp_path):
        src = tmp_path / 'src'
        dst = tmp_path / 'deep' / 'nested' / 'dst'
        _touch_preset(src, 'z.json')
        _create_manifest(src, 'z.json')
        _move_preset_files(src, dst)
        assert (dst / 'z.json').exists()

    def test_ignores_non_json_files(self, tmp_path):
        src = tmp_path / 'src'
        dst = tmp_path / 'dst'
        src.mkdir()
        (src / 'readme.txt').write_text('hi')
        _move_preset_files(src, dst)
        assert not (dst / 'readme.txt').exists()


class TestLoadManifestFilenames:
    def test_reads_filenames_from_valid_manifest(self, tmp_path):
        src = tmp_path / 'src'
        _create_manifest(src, 'alpha.json', 'beta.json')
        names = _load_manifest_filenames(src)
        assert names == {'alpha.json', 'beta.json'}

    def test_returns_empty_set_when_no_manifest(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        assert _load_manifest_filenames(src) == set()

    def test_returns_empty_set_on_corrupt_manifest(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        (src / 'manifest.json').write_text('NOT JSON }{')
        assert _load_manifest_filenames(src) == set()


# ---------------------------------------------------------------------------
# ensure_dir
# ---------------------------------------------------------------------------

class TestEnsureDir:
    def test_creates_presets_dir(self, tmp_path):
        config = PresetConfig(tmp_path)
        assert not config.presets_dir.exists()
        config.ensure_dir()
        assert config.presets_dir.is_dir()


# ---------------------------------------------------------------------------
# _run_installer uses configured presets_dir directly
# ---------------------------------------------------------------------------

class TestRunInstaller:
    """_run_installer must install to the configured presets_dir without needing
    write access to the app-data directory."""

    def test_installer_receives_configured_presets_dir(self, tmp_path, monkeypatch):
        """When config has a custom presets_dir, _run_installer must create an
        installer that targets that exact directory, not app_dir / 'presets'."""
        from is_matrix_forge.common.preset_config import _run_installer

        custom_dir = tmp_path / 'my custom presets'

        _write_json(
            tmp_path / SETTINGS_FILE_NAME,
            {'presets_dir': str(custom_dir)},
        )
        config = PresetConfig(tmp_path)
        assert config.presets_dir == custom_dir

        captured = {}

        class FakeInstaller:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            def run(self):
                return 0

        monkeypatch.setattr(
            'is_matrix_forge.led_matrix.scripts.install_presets.main.PresetInstaller',
            FakeInstaller,
        )
        import is_matrix_forge.common.preset_config as pc_mod
        monkeypatch.setattr(pc_mod, '_run_installer', lambda cfg: FakeInstaller(
            presets_dir=cfg.presets_dir,
        ).run())

        # Call the real _run_installer but intercept the PresetInstaller import
        # by patching the module-level name it uses.
        captured.clear()

        import sys
        original = sys.modules.get('is_matrix_forge.led_matrix.scripts.install_presets.main')

        fake_main = type(sys)('is_matrix_forge.led_matrix.scripts.install_presets.main')
        fake_main.PresetInstaller = FakeInstaller
        sys.modules['is_matrix_forge.led_matrix.scripts.install_presets.main'] = fake_main

        try:
            # Also stub GITHUB_REQ_HEADERS to avoid import chain
            import is_matrix_forge.led_matrix.constants as const_mod
            monkeypatch.setattr(const_mod, 'GITHUB_REQ_HEADERS', {}, raising=False)

            from is_matrix_forge.common.preset_config import _run_installer as real_run
            real_run(config)
        finally:
            if original is not None:
                sys.modules['is_matrix_forge.led_matrix.scripts.install_presets.main'] = original
            else:
                sys.modules.pop(
                    'is_matrix_forge.led_matrix.scripts.install_presets.main', None
                )

        assert 'presets_dir' in captured
        assert captured['presets_dir'] == custom_dir

    def test_installer_targets_configured_dir_not_parent_slash_presets(self, tmp_path):
        """Regression: the installer must NOT append '/presets' to the parent of
        the configured directory.  A user who has set 'matrix presets' as their
        directory should NOT end up with files in 'matrix presets/presets'."""
        custom_dir = tmp_path / 'matrix presets'
        custom_dir.mkdir()

        _write_json(
            tmp_path / SETTINGS_FILE_NAME,
            {'presets_dir': str(custom_dir)},
        )
        config = PresetConfig(tmp_path)

        # Whatever the installer does, it must target custom_dir, not
        # custom_dir.parent / 'presets'.
        wrong_dir = custom_dir.parent / 'presets'
        assert config.presets_dir == custom_dir
        assert config.presets_dir != wrong_dir
