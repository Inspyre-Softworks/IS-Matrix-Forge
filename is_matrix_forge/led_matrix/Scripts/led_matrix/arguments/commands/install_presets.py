from argparse import ArgumentParser

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
        default=None,
        help=(
            'Parent directory that will contain the ``presets`` subdirectory '
            '(i.e. presets land in ``<app-dir>/presets``). '
            'When omitted the currently-configured preset directory is used.'
        ),
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
