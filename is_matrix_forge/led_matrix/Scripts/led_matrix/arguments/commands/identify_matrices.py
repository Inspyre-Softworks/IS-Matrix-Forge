from argparse import ArgumentParser
from ....identify_matrices import DEFAULT_CYCLES, DEFAULT_RUNTIME


COMMAND = 'identify-matrices'


CONTROLLER_MAP = {
    'all': 'all',
    'l': 'leftmost',
    'r': 'rightmost'
}


HELP_TXT = ('Each found and configured controller will run the identification routine. This will have the device '
            'display it\'s own information.')


def register_command(parser: ArgumentParser):
    id_parser = parser.SUBCOMMANDS.add_parser(
        COMMAND,
        help=HELP_TXT
    )

    id_parser.add_argument(
        '--runtime', '-t',
        action='store',
        default=DEFAULT_RUNTIME,
        help='The total runtime'
    )

    id_parser.add_argument(
        '--skip-clear',
        action='store_true',
        default=False,
        help='Skip clearing LEDs'
    )

    id_parser.add_argument(
        '-c', '--cycle-count',
        action='store',
        type=int,
        default=DEFAULT_CYCLES,
        help='The number of cycles to run per message, for each selected device.'
    )

    # Set up the mutually exclusive arguments for the left and right matrices
    left_right = id_parser.add_mutually_exclusive_group()

    left_right.add_argument(
        '-R', '--only-right',
        action='store_true',
        default=False,
        help='Only display identifying information for/on the rightmost matrix.'
    )

    left_right.add_argument(
        '-L', '--only-left',
        action='store_true',
        default=False,
        help='Only display identifying information for/on the leftmost matrix.'
    )

    return id_parser
