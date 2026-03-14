from argparse import ArgumentParser

from is_matrix_forge.common.dirs import APP_DIRS
from is_matrix_forge.common.helpers.github_api import REPO_PRESETS_URL


COMMAND = 'install-presets'

HELP_TXT = (
    'Download and install JSON preset files from the project GitHub repository. '
    'Also removes the legacy LEDMatrixLib data directory if present.'
)


def register_command(parser: ArgumentParser):
    ip_parser = parser.SUBCOMMANDS.add_parser(
        COMMAND,
        help=HELP_TXT,
    )

    ip_parser.add_argument(
        '--url',
        default=REPO_PRESETS_URL,
        help='GitHub API URL to download presets from.',
    )

    ip_parser.add_argument(
        '--app-dir',
        default=str(APP_DIRS.user_data_path),
        help='Local directory in which presets are saved.',
    )

    ip_parser.add_argument(
        '--overwrite',
        action='store_true',
        default=False,
        help='Overwrite existing preset files.',
    )

    ip_parser.add_argument(
        '--no-progress',
        action='store_false',
        dest='with_progress',
        help='Disable progress bars.',
    )

    return ip_parser
