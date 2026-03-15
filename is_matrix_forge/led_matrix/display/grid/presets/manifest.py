"""
Author:
    Inspyre Softworks

Project:
    led-matrix-battery

File:
    is_matrix_forge/led_matrix/display/grid/presets/manifest.py

Description:
    Manages a JSON-based manifest mapping filenames to checksums,
    wrapped with metadata such as build version and save date.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Union
from datetime import datetime

from easy_exit_calls import ExitCallHandler
from is_matrix_forge.dev_tools.debug import is_debug_mode

ECH = ExitCallHandler()


def calculate_checksum(file_path: Union[str, Path]) -> str:
    """
    Calculates a SHA256 checksum for a file.

    Parameters:
        file_path (Union[str, Path]): Path to the file.

    Returns:
        str: Hex digest of the file's SHA256 checksum.
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


class GridPresetManifest:
    """
    Represents a manifest that maps preset filenames to their known checksums,
    along with versioning and date metadata.

    Automatically saves the manifest to disk when the program exits (in debug mode).
    """

    DEFAULT_VERSION = "dev"

    def __init__(self, manifest_path: Union[str, Path]):
        self.manifest_path = Path(manifest_path)
        self._manifest_dict: Dict[str, str] = {}
        self._meta: Dict[str, str] = {
            'version': self.DEFAULT_VERSION,
            'date': datetime.now().isoformat()
        }

        self._load()

        if is_debug_mode():
            ECH.register_handler(self._save)

    def _load(self):
        """
        Loads the manifest and metadata from disk if it exists.
        """
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    self._meta = data.get('meta', self._meta)
                    manifest = data.get('manifest', [])

                    self._manifest_dict = {
                        list(item.keys())[0]: list(item.values())[0]
                        for item in manifest
                    }

            except Exception as e:
                from is_matrix_forge.led_matrix.console import warning
                warning(f"[GridPresetManifest] Failed to load manifest: {e}")
        else:
            self._manifest_dict = {}

    def _save(self):
        """
        Saves the manifest and metadata to disk in JSON format.
        """
        try:
            self._meta['date'] = datetime.now().isoformat()
            data = {
                'meta': self._meta,
                'manifest': [{k: v} for k, v in self._manifest_dict.items()]
            }

            with open(self.manifest_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            from is_matrix_forge.led_matrix.console import warning
            warning(f"[GridPresetManifest] Failed to save manifest: {e}")

    def get_checksum(self, filename: str) -> Optional[str]:
        """
        Returns the stored checksum for a given file.

        Parameters:
            filename (str): Name of the file to query.

        Returns:
            Optional[str]: Checksum string or None.
        """
        return self._manifest_dict.get(filename)

    def add(self, filename: str, checksum: str):
        """
        Adds or updates a checksum entry in the manifest.

        Parameters:
            filename (str): File name.
            checksum (str): Checksum string.
        """
        self._manifest_dict[filename] = checksum

    def scan(self, dir_path: Union[str, Path]):
        """
        Scans a directory for files and adds their checksums to the manifest.

        Parameters:
            dir_path (Union[str, Path]): Directory path.
        """
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            raise ValueError(f"{dir_path} is not a valid directory")

        for file in dir_path.iterdir():
            if file.is_file():
                checksum = calculate_checksum(file)
                self.add(file.name, checksum)

    def __getitem__(self, filename: str) -> Optional[str]:
        return self.get_checksum(filename)

    def __setitem__(self, filename: str, checksum: str):
        self.add(filename, checksum)

    def __contains__(self, filename: str) -> bool:
        return filename in self._manifest_dict

    def as_dict(self) -> Dict[str, str]:
        """
        Returns a copy of the manifest dictionary.
        """
        return self._manifest_dict.copy()

    def get_meta(self) -> Dict[str, str]:
        """
        Returns a copy of the metadata dictionary.
        """
        return self._meta.copy()

    def set_version(self, version: str):
        """
        Sets the version in metadata.

        Parameters:
            version (str): Version string.
        """
        self._meta['version'] = version
