"""
Directory configuration for the IS-Matrix-Forge application.

This module provides platform-specific directory paths for storing application
data, configuration files, and other resources using the platformdirs library.

``PRESETS_DIR`` is derived from :class:`~is_matrix_forge.common.preset_config.PresetConfig`
so that any user-configured preset location is always honoured.

``ANIMATIONS_DIR`` is the default per-user directory for JSON animation files
loaded by :class:`~is_matrix_forge.led_matrix.controller.components.animation.AnimationManager`.
"""

from platformdirs import PlatformDirs

from is_matrix_forge.common.preset_config import get_preset_config


APP_DIRS = PlatformDirs('IS-Matrix-Forge', appauthor='Inspyre Softworks')
APP_DIR  = APP_DIRS.user_data_path
ANIMATIONS_DIR = APP_DIR / 'animations'
"""Default per-user directory for name-addressable JSON animations."""

# Read the user-configured preset directory; falls back to APP_DIR/presets.
PRESETS_DIR = get_preset_config().presets_dir


__all__ = [
    'APP_DIRS',
    'APP_DIR',
    'ANIMATIONS_DIR',
    'PRESETS_DIR',
]
