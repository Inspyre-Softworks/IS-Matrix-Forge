"""


Author: 
    Inspyre Softworks

Project:
    IS-Matrix-Forge

File: 
    is_matrix_forge/dev_tools/presets.py
 

Description:
    

"""
from is_matrix_forge.led_matrix.constants import PROJECT_URLS
import requests


MANIFEST_FILE_NAME = 'manifest.json'
REMOTE_MANIFEST_URL = PROJECT_URLS['github_api'] + '/' + MANIFEST_FILE_NAME


def get_remote_manifest():
    """
    Download the remote preset manifest file.

    Returns:
        dict:
            The JSON content of the remote manifest file.

    Raises:
        requests.RequestException:
            If there is an error during the HTTP request.
    """
    res = requests.get(REMOTE_MANIFEST_URL)
    res.raise_for_status()

    data = res.json()

    return data

