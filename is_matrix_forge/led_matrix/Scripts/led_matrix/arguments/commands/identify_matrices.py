from argparse import ArgumentParser
from ....identify_matrices import DEFAULT_CYCLES, DEFAULT_RUNTIME

from . import add_matrix_selection_args


COMMAND = 'identify-matrices'


HELP_TXT = (
    'Each found and configured controller will run the identification routine.'
)


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

    add_matrix_selection_args(id_parser)

    return id_parser
