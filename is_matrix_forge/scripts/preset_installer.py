"""
Author: Taylor B.
Project: led-matrix-battery

File: preset_installer.py

Description:
    Provides a CLI to download JSON preset files from the GitHub repository and save them locally,
    ensuring local files are fresh by verifying and re-downloading if checksums differ.

Classes:
    - PresetInstaller

Functions:
    - main

Constants:
    - API_URL
    - REQ_HEADERS
    - REPO_PRESETS_URL

Dependencies:
    - typing
    - pathlib
    - requests
    - tqdm
    - inspy_logger
    - inspyre_toolbox.path_man.provision_path
    - is_matrix_forge.common.helpers.verify_checksum
    - is_matrix_forge.led_matrix.constants.PROJECT_URLS, APP_DIRS
    - is_matrix_forge.common.helpers.github_api.assemble_github_content_path_url
    - is_matrix_forge.led_matrix.display.grid.presets.manifest.GridPresetManifest

Example Usage:
    python -m is_matrix_forge.preset_installer \
        --app-dir /path/to/data \
        --overwrite \
        --no-progress
"""

import argparse
from typing import List, Dict, Optional, Union
from pathlib import Path
import requests
import hashlib
from tqdm import tqdm

from is_matrix_forge.led_matrix.constants import PROJECT_URLS, APP_DIRS
from is_matrix_forge.led_matrix.display.grid.presets.manifest import GridPresetManifest
from inspy_logger import InspyLogger
from inspyre_toolbox.path_man import provision_path
from is_matrix_forge.common.helpers.github_api import assemble_github_content_path_url as assemble_url

LOGGER = InspyLogger('LEDMatrixLib:PresetInstaller', console_level='debug', no_file_logging=True)

API_URL = PROJECT_URLS['github_api']
REQ_HEADERS = {"Accept": "application/vnd.github.v3+json"}
REPO_PRESETS_URL = assemble_url('presets')


def github_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


class PresetInstaller:
    def __init__(
        self,
        url: str = REPO_PRESETS_URL,
        headers: Optional[Dict[str, str]] = None,
        app_dir: Union[str, Path] = APP_DIRS.user_data_path,
        overwrite_existing: bool = False,
        with_progress: bool = True
    ):
        self.url = url
        self.headers = headers or REQ_HEADERS
        self.app_dir = provision_path(app_dir)
        self.overwrite = overwrite_existing
        self.with_progress = with_progress

        self.presets_dir = self.app_dir / 'presets'
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        self.log = LOGGER.get_child(self.__class__.__name__)

    def run(self):
        self.log.debug(f"Fetching file list from {self.url}")
        files = self.get_file_list()
        iterator = tqdm(files, desc="Processing files", unit="file") if self.with_progress else files

        for f in iterator:
            if self._is_json(f):
                self._process_file(f)
            else:
                self.log.debug(f"Skipping non-JSON file: {f.get('name')}")

        manifest_path = self.presets_dir / "manifest.json"
        manifest = GridPresetManifest(manifest_path)
        manifest.scan(self.presets_dir)

    def get_file_list(self) -> List[Dict]:
        res = requests.get(self.url, headers=self.headers)
        res.raise_for_status()
        return res.json()

    def _is_json(self, file_info: Dict) -> bool:
        return file_info.get('type') == 'file' and file_info.get('name', '').endswith('.json')

    def _process_file(self, file_info: Dict):
        name = file_info['name']
        local_path = self.presets_dir / name

        res = requests.get(file_info['download_url'])
        res.raise_for_status()
        content = res.content

        actual_sha = github_blob_sha(content)
        expected_sha = file_info['sha']

        if actual_sha != expected_sha:
            self.log.error(f"GitHub SHA mismatch for {name}")
            raise ValueError(f"GitHub blob SHA mismatch for {name}")

        self.save_file(local_path, content.decode('utf-8'), overwrite=True)

    def _download_file(self, file_info: Dict, local_path: Path):
        if self.with_progress:
            self._download_with_progress(file_info, local_path)
        else:
            self._download_simple(file_info, local_path)

    def _download_simple(self, file_info: Dict, local_path: Path):
        res = requests.get(file_info['download_url'])
        res.raise_for_status()
        self.save_file(local_path, res.content.decode('utf-8'), overwrite=True)

    def _download_with_progress(self, file_info: Dict, local_path: Path):
        url = file_info['download_url']
        res = requests.get(url, stream=True)
        res.raise_for_status()
        total = int(res.headers.get('content-length', 0))
        bar = tqdm(total=total, unit='B', unit_scale=True, desc=f"Downloading {file_info['name']}", leave=False)

        chunks = []
        for chunk in res.iter_content(chunk_size=1024):
            if chunk:
                chunks.append(chunk)
                bar.update(len(chunk))
        bar.close()

        content = b''.join(chunks).decode('utf-8')
        self.save_file(local_path, content, overwrite=True)

    @staticmethod
    def save_file(path: Path, data: str, overwrite: bool = False):
        path = provision_path(path)
        if path.exists() and not overwrite:
            LOGGER.get_child('save_file').warning(f"Skipping existing file {path}")
            return
        with open(path, 'w') as f:
            f.write(data)
        LOGGER.get_child('save_file').debug(f"Wrote file {path}")


def main():
    parser = argparse.ArgumentParser(description="Install JSON presets from GitHub")
    parser.add_argument('--url', help="GitHub API URL for presets", default=REPO_PRESETS_URL)
    parser.add_argument('--app-dir', help="Local directory to save presets", default=str(APP_DIRS.user_data_path))
    parser.add_argument('--overwrite', help="Overwrite existing files", action='store_true')
    parser.add_argument('--no-progress', help="Disable progress bars", action='store_false', dest='with_progress')

    args = parser.parse_args()

    installer = PresetInstaller(
        url=args.url,
        headers=REQ_HEADERS,
        app_dir=args.app_dir,
        overwrite_existing=args.overwrite,
        with_progress=args.with_progress
    )
    installer.run()


if __name__ == '__main__':
    main()
