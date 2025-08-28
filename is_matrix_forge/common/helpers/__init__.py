import hashlib
from pathlib import Path
from typing import Optional
try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    requests = None
try:
    from inspyre_toolbox.path_man import provision_path
except ModuleNotFoundError:  # pragma: no cover - fallback
    def provision_path(path):
        return Path(path)
from is_matrix_forge.log_engine import ROOT_LOGGER


MOD_LOGGER = ROOT_LOGGER.get_child(__name__)


def download_presets():
    from is_matrix_forge.led_matrix.constants import PROJECT_URLS

    url = PROJECT_URLS['github_api']



def calculate_checksum(file_path):
    """
    Calculate the SHA-256 checksum of a file.

    Parameters:
        file_path (Union[str, Path]):
            The path to the file for which to calculate the checksum.

    Returns:
        str:
            The SHA-256 checksum of the file.
    """
    log = MOD_LOGGER.get_child('calculate_checksum')

    if not isinstance(file_path, Path):
        file_path = provision_path(file_path)

    log.debug(f'Calculating checksum for file: {file_path}')

    sha256 = hashlib.sha256()

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)

    return sha256.hexdigest()


def coerce_to_int(value) -> Optional[int]:
    """
    Attempt to coerce a value to an integer.

    Parameters:
        value (Any):
            The value to coerce.

    Returns:
        Optional[int]:
            The coerced integer value, or None if the coercion fails.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def percentage_to_value(percent, max_value=255):
    """
    Convert a percentage value to an actual value between 0 and `max_value`.

    Parameters:
        percent (float):
            The percentage value to convert.

        max_value (int, optional):
            The maximum value to which the percentage should be converted. Defaults to 255.

    Returns:
        int:
            The converted value between 0 and `max_value`.
    """
    if not isinstance(percent, (int, float)):
        raise TypeError(f'percent must be of type int or float, not {type(percent)}')

    if percent < 0 or percent > 100:
        raise ValueError(f'percent must be between 0 and 100, not {percent}')

    return int(round(percent * max_value / 100))


def value_to_percentage(value, max_value=255):
    """
    Convert a value to its percentage representation relative to `max_value`.

    Parameters:
        value (int or float):
            The value to convert.

        max_value (int, optional):
            The maximum possible value. Defaults to 255.

    Returns:
        float:
            The percentage value between 0 and 100.
    """
    if not isinstance(value, (int, float)):
        raise TypeError(f'value must be of type int or float, not {type(value)}')

    if value < 0 or value > max_value:
        raise ValueError(f'value must be between 0 and {max_value}, not {value}')

    return (value / max_value) * 100


def verify_checksum(remote_checksum, local_file_path):
    """
    Verify the checksum of a local file against a remote checksum.

    Parameters:
        remote_checksum (str):
            The remote checksum to verify against.

        local_file_path (Union[str, Path]):
            The path to the local file to verify.

    Returns:
        bool:
            True if the checksums match, False otherwise.
    """
    if not isinstance(local_file_path, Path):
        local_file_path = provision_path(local_file_path)

    sha256 = hashlib.sha256()

    with open(local_file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)

    local_checksum = sha256.hexdigest()

    return local_checksum == remote_checksum


def download_file(url, local_path, headers=None):
    """
    Download a file from a URL and save it to a local path.

    Parameters:
        url (str):
            The URL of the file to download.

        local_path (Union[str, Path]):
            The local path to save the downloaded file.

        headers (Optional[Dict]):
            The headers to use for the request. Defaults to None.
    """
    if not isinstance(local_path, Path):
        local_path = provision_path(local_path)

    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
