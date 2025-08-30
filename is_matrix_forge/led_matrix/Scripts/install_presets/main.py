"""
Author:
    Taylor B.

Project:
    led-matrix-battery

File:
    is_matrix_forge/led_matrix/Scripts/install_presets/main.py

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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from is_matrix_forge.progress import tqdm

from is_matrix_forge.led_matrix.constants import PROJECT_URLS, APP_DIRS, GITHUB_REQ_HEADERS as REQ_HEADERS
from is_matrix_forge.led_matrix.display.grid.presets.manifest import GridPresetManifest
from inspy_logger import InspyLogger, Loggable
from inspyre_toolbox.path_man import provision_path
from is_matrix_forge.common.helpers.github_api import assemble_github_content_path_url as assemble_url, REPO_PRESETS_URL

LOGGER = InspyLogger('LEDMatrixLib:PresetInstaller', console_level='info', no_file_logging=True)


def github_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


class PresetInstaller(Loggable):
    def __init__(
            self,
            url: str = REPO_PRESETS_URL,
            headers: Optional[Dict[str, str]] = None,
            app_dir: Union[str, Path] = APP_DIRS.user_data_path,
            overwrite_existing: bool = False,
            with_progress: bool = True,
            timeout: float = 15.0,
    ):
        super().__init__(LOGGER)
        self.url = url
        self.headers = headers or REQ_HEADERS
        self.app_dir = provision_path(app_dir)
        self.overwrite = overwrite_existing
        self.with_progress = with_progress
        self.timeout = timeout

        self.presets_dir = self.app_dir / 'presets'
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        self.log = self.class_logger

        # HTTP session for connection reuse
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def run(self):
        log = self.method_logger
        log.debug(f"Fetching file list from {self.url}")
        try:
            files = self.get_file_list()
        except requests.RequestException as e:
            log.error(f"Failed to fetch file list: {e}")
            return 1
        iterator = tqdm(files, desc="Processing files", unit="file") if self.with_progress else files

        for f in iterator:
            if self._is_json(f):
                try:
                    self._process_file(f)
                except requests.RequestException as e:
                    log.error(f"Failed to download {f.get('name')}: {e}")
                except Exception as e:
                    log.error(f"Error processing {f.get('name')}: {e}")
            else:
                log.debug(f"Skipping non-JSON file: {f.get('name')}")

        manifest_path = self.presets_dir / "manifest.json"
        manifest = GridPresetManifest(manifest_path)
        manifest.scan(self.presets_dir)
        return 0

    def get_file_list(self) -> List[Dict]:
        res = self.session.get(self.url, timeout=self.timeout)
        res.raise_for_status()
        data = res.json()
        if not isinstance(data, list):
            raise ValueError("Unexpected response format from GitHub API: expected a list")
        return data

    @staticmethod
    def _is_json(file_info: Dict) -> bool:
        """
        Upon receipt of file info, verify that it's for a JSON file (has the .json extension).
        """
        return file_info.get('type') == 'file' and file_info.get('name', '').endswith('.json')

    def _process_file(self, file_info: Dict):
        name = file_info['name']
        local_path = self.presets_dir / name

        res = self.session.get(file_info['download_url'], timeout=self.timeout)
        res.raise_for_status()
        content = res.content

        actual_sha = github_blob_sha(content)
        expected_sha = file_info['sha']

        if actual_sha != expected_sha:
            self.log.error(f"GitHub SHA mismatch for {name}")
            raise ValueError(f"GitHub blob SHA mismatch for {name}")

        # If file exists and overwrite is false, skip when content matches
        if local_path.exists() and not self.overwrite:
            try:
                with open(local_path, 'rb') as f:
                    local_bytes = f.read()
                local_sha = github_blob_sha(local_bytes)
                if local_sha == actual_sha:
                    self.log.debug(f"Up-to-date: {name} (checksum match)")
                    return
                else:
                    self.log.info(f"Updating changed preset: {name}")
            except Exception:
                # If we can't read/compare, fall back to writing based on overwrite flag below
                pass

        self.save_file(local_path, content.decode('utf-8'), overwrite=self.overwrite)

    def _download_file(self, file_info: Dict, local_path: Path):
        if self.with_progress:
            self._download_with_progress(file_info, local_path)
        else:
            self._download_simple(file_info, local_path)

    def _download_simple(self, file_info: Dict, local_path: Path):
        res = self.session.get(file_info['download_url'], timeout=self.timeout)
        res.raise_for_status()
        self.save_file(local_path, res.content.decode('utf-8'), overwrite=self.overwrite)

    def _download_with_progress(self, file_info: Dict, local_path: Path):
        url = file_info['download_url']
        res = self.session.get(url, stream=True, timeout=self.timeout)
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
        self.save_file(local_path, content, overwrite=self.overwrite)

    def save_file(self, path: Path, data: str, overwrite: bool = False):
        log = self.method_logger
        path = provision_path(path)
        if path.exists() and not overwrite:
            log.warning(f"Skipping existing file {path}")
            return
        with open(path, 'w') as f:
            f.write(data)
        log.debug(f"Wrote file {path}")


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
    exit_code = installer.run()
    if isinstance(exit_code, int):
        raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
