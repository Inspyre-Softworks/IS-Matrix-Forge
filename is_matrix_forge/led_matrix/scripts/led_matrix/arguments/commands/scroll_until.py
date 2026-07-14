from argparse import ArgumentParser

from . import add_matrix_selection_args


COMMAND = 'scroll-until'

HELP_TXT = (
    'Scroll text on the selected matrix until an external command finishes. '
    'Use --on-complete to control what happens to the display when the command exits.'
)


def register_command(parser: ArgumentParser):
    su_parser = parser.SUBCOMMANDS.add_parser(
        COMMAND,
        help=HELP_TXT,
    )

    su_parser.add_argument(
        'input',
        type=str,
        help='Text to scroll while waiting for the command to finish.',
    )

    su_parser.add_argument(
        'command',
        type=str,
        help='Shell command to run. Scrolling continues until this command exits.',
    )

    su_parser.add_argument(
        '--on-complete',
        choices=['clear', 'leave', 'fade'],
        default='clear',
        help=(
            'Action to take on the matrix when the command finishes. '
            '"clear" blanks the display (default), "leave" keeps the last frame, '
            '"fade" gradually dims to black then clears.'
        ),
    )

    add_matrix_selection_args(su_parser)

    return su_parser
