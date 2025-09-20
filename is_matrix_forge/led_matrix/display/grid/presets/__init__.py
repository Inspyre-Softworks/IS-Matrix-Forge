"""
Grid presets module for LED Matrix display.

Author: 
    Inspyre Softworks

Project:
    led-matrix-battery

File: 
    is_matrix_forge/led_matrix/display/grid/presets/base.py

Description:
    This module provides functionality for managing grid presets for the LED matrix display.
    It includes a manifest of available presets and validation functions.
"""
from pathlib import Path
from typing import Optional

from is_matrix_forge.common.helpers import verify_checksum
from is_matrix_forge.led_matrix.constants import PRESETS_DIR
from is_matrix_forge.led_matrix.display.grid.presets.manifest import GridPresetManifest


PRESETS_MANIFEST = GridPresetManifest(PRESETS_DIR / 'manifest.json')


def validate_preset_files(preset_dir_path: Optional[Path] = None, manifest: Optional[GridPresetManifest] = None) -> bool:
    """
    Validate that all preset files in the manifest exist and are valid.

    Args:
        preset_dir_path (Optional[Path], optional): 
            The directory containing preset files. Defaults to PRESETS_DIR if None.
        manifest (Optional[GridPresetManifest], optional): 
            The manifest to validate against. Defaults to PRESETS_MANIFEST if None.

    Returns:
        bool: True if all preset files are valid, False otherwise.

    Note:
        Validation checks that each file listed in the manifest exists in the
        preset directory and that its checksum matches the value stored in the
        manifest.
    """

    preset_dir_path = preset_dir_path or PRESETS_DIR
    manifest = manifest or PRESETS_MANIFEST

    if not isinstance(preset_dir_path, Path):
        preset_dir_path = Path(preset_dir_path)

    all_valid = True

    for filename, checksum in manifest.as_dict().items():
        file_path = preset_dir_path / filename
        if not file_path.exists():
            all_valid = False
            break
        if not verify_checksum(checksum, file_path):
            all_valid = False
            break

    return all_valid
