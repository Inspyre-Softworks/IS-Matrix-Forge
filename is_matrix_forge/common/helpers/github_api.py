"""


Author: 
    Inspyre Softworks

Project:
    IS-Matrix-Forge

File: 
    is_matrix_forge/common/helpers/github_api.py
 

Description:
    

"""
from typing import Optional
from is_matrix_forge.led_matrix.constants import PROJECT_URLS

GITHUB_URL_SUFFIX = '?ref=main'


def assemble_github_url_suffix(branch: Optional[str] = None):
    """
    Assemble the URL suffix for the GitHub link.

    Parameters:
        branch (Optional[str]):
            The name of the target GitHub repo branch.
            Optional, defaults to "main".

    Returns:
        str:
            The GitHub URL suffix. Specifically, a reference tag to a target branch.
    """
    return f'?ref={branch or "main"}'


def assemble_github_content_path_url(
        relative_path: Optional[str] = 'presets',  # e.g. 'dev_tools/presets.py'
        branch:        Optional[str] = 'master',
        base_url:      Optional[str] = PROJECT_URLS['github_api'],
        suffix:        Optional[str] = None
):
    """
    Assemble a GitHub content path URL.

    Parameters:
        relative_path (Optional[str]):
            The relative path to the file in the GitHub repository.
        branch (Optional[str]):
            The branch name. Defaults to 'master'.
        base_url (Optional[str]):
            The base URL of the GitHub API. Defaults to PROJECT_URLS['github_api'].
        suffix (Optional[str]):
            The URL suffix. Defaults to GITHUB_URL_SUFFIX.

    Returns:
        str:
            The assembled GitHub content path URL.
    """
    return f"{base_url}/{relative_path}{suffix or assemble_github_url_suffix(branch)}"


REPO_PRESETS_URL = assemble_github_content_path_url()

