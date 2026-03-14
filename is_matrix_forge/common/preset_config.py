"""
Preset directory configuration and on-load presence check for IS-Matrix-Forge.

This module owns three responsibilities:

1. **Settings persistence** – ``PresetConfig`` stores the user-configured
   preset directory path in ``<app-data>/settings.json``.

2. **Automatic migration** – When the configured path differs from the
   location where preset files actually live (e.g. because the user edited
   ``settings.json`` by hand), ``PresetConfig.reconcile()`` moves the files
   to the new location before anything else touches them.

3. **Startup prompt** – ``check_and_prompt_presets()`` is called once per
   Python process when the ``led_matrix`` sub-package is imported.  It does
   nothing in non-interactive environments; in a TTY it offers to download
   the presets with a single key-press if they are absent.
"""

from __future__ import annotations

import json
import shutil
import sys
import threading
import warnings
from pathlib import Path
from typing import Union

# Module-level guard: only prompt once per Python process.
_STARTUP_CHECK_LOCK: threading.Lock = threading.Lock()
_STARTUP_CHECK_DONE: bool = False

SETTINGS_FILE_NAME = 'settings.json'
_PRESETS_DIR_KEY   = 'presets_dir'


# ---------------------------------------------------------------------------
# Internal file-move helper
# ---------------------------------------------------------------------------

def _load_manifest_filenames(src: Path) -> set:
    """Return the set of filenames recorded in *src/manifest.json*.

    Returns an empty set when the manifest is absent or unreadable so the
    caller can fall back to moving nothing (safe default).
    """
    manifest_path = src / 'manifest.json'
    if not manifest_path.exists():
        return set()
    try:
        import json as _json
        with open(manifest_path, 'r', encoding='utf-8') as fh:
            data = _json.load(fh)
        if isinstance(data, dict):
            entries = data.get('manifest', [])
            return {list(e.keys())[0] for e in entries if isinstance(e, dict) and e}
    except Exception:
        pass
    return set()


def _move_preset_files(src: Path, dst: Path) -> bool:
    """Move only the manifest-tracked ``*.json`` preset files from *src* to *dst*.

    Files that exist in *src* but are **not** listed in the manifest are left
    untouched — they belong to the user and must never be deleted or moved
    without explicit consent.

    The ``manifest.json`` itself is also moved so the destination is fully
    self-contained.

    Returns:
        ``True`` if *src* is empty (or no longer exists) after the operation —
        i.e. it is safe for the caller to remove *src*.  ``False`` if files
        remain (user files were skipped).
    """
    dst.mkdir(parents=True, exist_ok=True)

    manifest_names = _load_manifest_filenames(src)

    for preset_file in src.glob('*.json'):
        # Only migrate files that are explicitly listed in the manifest.
        # manifest.json itself is always eligible.
        if preset_file.name != 'manifest.json' and preset_file.name not in manifest_names:
            continue
        try:
            shutil.move(str(preset_file), dst / preset_file.name)
        except Exception as exc:
            warnings.warn(
                f'Could not move preset file {preset_file.name} to {dst}: {exc}',
                RuntimeWarning,
                stacklevel=2,
            )

    # Report whether the source directory is now empty.
    try:
        remaining = list(src.iterdir())
        return len(remaining) == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# PresetConfig
# ---------------------------------------------------------------------------

class PresetConfig:
    """Manages the preset directory setting with automatic file-move support.

    The configuration is persisted as JSON at::

        <app_dir>/settings.json

    Example content::

        {
          "presets_dir": "/home/alice/.local/share/IS-Matrix-Forge/presets"
        }

    Changing :attr:`presets_dir` via the property setter automatically moves
    any existing ``.json`` preset files from the old location to the new one.
    """

    def __init__(self, app_dir: Union[str, Path]) -> None:
        self._app_dir       = Path(app_dir)
        self._settings_file = self._app_dir / SETTINGS_FILE_NAME
        self._settings: dict = self._load()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _default_presets_dir(self) -> Path:
        return self._app_dir / 'presets'

    def _load(self) -> dict:
        if self._settings_file.exists():
            try:
                with open(self._settings_file, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        return {}

    def _save(self) -> None:
        self._app_dir.mkdir(parents=True, exist_ok=True)
        with open(self._settings_file, 'w', encoding='utf-8') as fh:
            json.dump(self._settings, fh, indent=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def presets_dir(self) -> Path:
        """Current configured presets directory.

        Falls back to ``<app_dir>/presets`` when not explicitly set.
        """
        raw = self._settings.get(_PRESETS_DIR_KEY)
        return Path(raw) if raw else self._default_presets_dir()

    @presets_dir.setter
    def presets_dir(self, new_path: Union[str, Path]) -> None:
        """Change the presets directory and move manifest-tracked files there.

        Only files listed in the source manifest are moved.  Any other files
        the user may have placed in the old directory are left untouched.  The
        old directory is removed only when it is completely empty after the
        migration.

        Parameters:
            new_path:
                Absolute path to the desired preset directory.
        """
        new_path = Path(new_path)
        old_path = self.presets_dir

        if new_path == old_path:
            return

        if old_path.is_dir() and any(old_path.glob('*.json')):
            src_empty = _move_preset_files(old_path, new_path)
            if src_empty:
                try:
                    old_path.rmdir()
                except Exception:
                    pass

        self._settings[_PRESETS_DIR_KEY] = str(new_path)
        self._save()

    def has_presets(self) -> bool:
        """Return ``True`` if at least one ``.json`` preset file is present."""
        return bool(list(self.presets_dir.glob('*.json')))

    def reconcile(self) -> None:
        """Migrate preset files when the configured path has changed.

        This handles the case where a user manually edits ``settings.json``
        to point ``presets_dir`` at a new path: the files still live at the
        default location, so this method moves them across automatically.

        Only files listed in the source manifest are moved.  User files not
        tracked by the manifest are left in place.  The source directory is
        removed only when it is empty after the migration.

        The reconciliation only happens when:

        * The configured path does **not** already contain preset files, *and*
        * The default path **does** contain preset files, *and*
        * The two paths are different.
        """
        desired = self.presets_dir
        default = self._default_presets_dir()

        # Nothing to do – files already live at the configured location.
        if desired.is_dir() and any(desired.glob('*.json')):
            return

        # Move manifest-tracked files from default to desired.
        if desired != default and default.is_dir() and any(default.glob('*.json')):
            src_empty = _move_preset_files(default, desired)
            if src_empty:
                try:
                    default.rmdir()
                except Exception:
                    pass
            self._settings[_PRESETS_DIR_KEY] = str(desired)
            self._save()

    def ensure_dir(self) -> None:
        """Create the preset directory if it does not already exist."""
        self.presets_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def get_preset_config() -> PresetConfig:
    """Return a :class:`PresetConfig` rooted at the application data directory."""
    from is_matrix_forge.common.dirs import APP_DIR  # lazy to avoid circular import
    return PresetConfig(APP_DIR)


def check_and_prompt_presets() -> None:
    """Check whether presets are present; offer to download them if not.

    This function is designed to be called once at package-import time.  It:

    * Runs at most once per Python process.  A :class:`threading.Lock` prevents
      simultaneous execution from multiple threads that might import the package
      concurrently.
    * Calls :meth:`PresetConfig.reconcile` to move any files whose location
      was changed via ``settings.json``.
    * Skips silently in non-interactive environments (no TTY, CI pipelines,
      etc.).
    * Never raises – any exception is swallowed so that a config problem
      cannot crash an unrelated user script.

    To trigger a download the user can also run::

        led-matrix install-presets
    """
    global _STARTUP_CHECK_DONE

    with _STARTUP_CHECK_LOCK:
        if _STARTUP_CHECK_DONE:
            return
        _STARTUP_CHECK_DONE = True

    try:
        config = get_preset_config()
        config.reconcile()

        if config.has_presets():
            return

        # Only prompt in interactive terminals.
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            return

        print(
            '\n[IS-Matrix-Forge] No preset files were found in:\n'
            f'  {config.presets_dir}\n'
            'Run  led-matrix install-presets  to download them.'
        )
        try:
            answer = input('Download presets now? [y/N] ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if answer in ('y', 'yes'):
            _run_installer(config)

    except Exception:
        # Never let the startup check crash a user's script.
        pass


def _run_installer(config: PresetConfig) -> None:
    """Silently run the preset installer using the configured preset directory."""
    try:
        from is_matrix_forge.led_matrix.Scripts.install_presets.main import PresetInstaller
        from is_matrix_forge.led_matrix.constants import GITHUB_REQ_HEADERS

        installer = PresetInstaller(
            app_dir=config.presets_dir.parent,
            headers=GITHUB_REQ_HEADERS,
            overwrite_existing=False,
            with_progress=True,
        )
        installer.run()
    except Exception as exc:
        print(f'[IS-Matrix-Forge] Preset installation failed: {exc}')


__all__ = [
    'PresetConfig',
    'check_and_prompt_presets',
    'get_preset_config',
    'SETTINGS_FILE_NAME',
]
