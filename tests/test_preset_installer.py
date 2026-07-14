"""Tests for PresetInstaller – focusing on the presets_dir parameter and the
fix for the 'Permission denied' bug that occurred when the installer tried to
create the default app-data directory even though the user had configured a
custom preset location."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest


# ---------------------------------------------------------------------------
# Stub heavy optional dependencies before any is_matrix_forge import.
# Same pattern as test_preset_config.py so the stubs are compatible when the
# full test suite runs together.
# ---------------------------------------------------------------------------

def _install_test_stubs() -> None:
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
    }
    for mod_name, attrs in stubs.items():
        if mod_name not in sys.modules:
            m = ModuleType(mod_name)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[mod_name] = m

    # Stub the presets manifest package so the module-level
    # ``PRESETS_MANIFEST = GridPresetManifest(...)`` call in its __init__ does
    # not try to access the real filesystem (which may be broken in CI).
    for mod_name in (
        'is_matrix_forge.led_matrix.display.grid.presets',
        'is_matrix_forge.led_matrix.display.grid.presets.manifest',
    ):
        if mod_name not in sys.modules:
            m = ModuleType(mod_name)
            sys.modules[mod_name] = m

    presets_manifest_mod = sys.modules['is_matrix_forge.led_matrix.display.grid.presets.manifest']
    if not hasattr(presets_manifest_mod, 'GridPresetManifest'):
        class _FakeManifest:
            def __init__(self, *a, **kw):
                pass
            def scan(self, *a, **kw):
                pass
        presets_manifest_mod.GridPresetManifest = _FakeManifest

    presets_pkg_mod = sys.modules['is_matrix_forge.led_matrix.display.grid.presets']
    if not hasattr(presets_pkg_mod, 'GridPresetManifest'):
        presets_pkg_mod.GridPresetManifest = presets_manifest_mod.GridPresetManifest
    if not hasattr(presets_pkg_mod, 'PRESETS_MANIFEST'):
        presets_pkg_mod.PRESETS_MANIFEST = presets_manifest_mod.GridPresetManifest()


_install_test_stubs()


# ---------------------------------------------------------------------------
# PresetInstaller: presets_dir parameter
# ---------------------------------------------------------------------------
# We import PresetInstaller lazily inside each test (or fixture) so that the
# full stub environment is in place before the module-level LOGGER is created.

@pytest.fixture()
def PresetInstaller(monkeypatch, tmp_path):
    """Return PresetInstaller with heavy external deps patched away."""
    # Import the module first so monkeypatch can reach its attributes.
    import inspyre_toolbox.path_man as _ptm
    monkeypatch.setattr(_ptm, 'provision_path', lambda p: Path(p))

    from is_matrix_forge.led_matrix.scripts.install_presets.main import (
        PresetInstaller as _PI,
    )
    return _PI


class TestPresetInstallerPresetsDir:
    def test_presets_dir_param_overrides_app_dir(self, PresetInstaller, tmp_path):
        """When presets_dir is given, it is used directly."""
        custom_dir = tmp_path / 'my custom presets'
        installer = PresetInstaller(presets_dir=custom_dir)
        assert installer.presets_dir == custom_dir
        assert custom_dir.is_dir(), 'presets_dir must be created'

    def test_presets_dir_does_not_append_presets_subdir(self, PresetInstaller, tmp_path):
        """Regression: installer.presets_dir must NOT be presets_dir / 'presets'."""
        custom_dir = tmp_path / 'matrix presets'
        installer = PresetInstaller(presets_dir=custom_dir)
        wrong = custom_dir / 'presets'
        assert installer.presets_dir == custom_dir
        assert installer.presets_dir != wrong

    def test_presets_dir_not_parent_slash_presets(self, PresetInstaller, tmp_path):
        """Regression: installer must NOT recompute the dir as parent / 'presets'."""
        custom_dir = tmp_path / 'matrix presets'
        installer = PresetInstaller(presets_dir=custom_dir)
        wrong = custom_dir.parent / 'presets'
        assert installer.presets_dir != wrong
        assert installer.presets_dir == custom_dir

    def test_app_dir_derived_from_presets_dir_parent(self, PresetInstaller, tmp_path):
        """When presets_dir is given, app_dir is set to its parent."""
        custom_dir = tmp_path / 'presets'
        installer = PresetInstaller(presets_dir=custom_dir)
        assert installer.app_dir == custom_dir.parent

    def test_legacy_app_dir_still_works(self, PresetInstaller, tmp_path):
        """Existing callers that pass app_dir without presets_dir still work."""
        installer = PresetInstaller(app_dir=tmp_path)
        assert installer.presets_dir == tmp_path / 'presets'
        assert installer.app_dir == tmp_path

    def test_presets_dir_created_automatically(self, PresetInstaller, tmp_path):
        """The target directory is created during __init__ if it does not exist."""
        target = tmp_path / 'nested' / 'preset dir'
        assert not target.exists()
        PresetInstaller(presets_dir=target)
        assert target.is_dir()
