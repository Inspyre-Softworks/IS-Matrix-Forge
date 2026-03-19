from argparse import ArgumentParser

from . import add_matrix_selection_args


DIRECTION_MAP = {
    'up': 'vertical_down',
    'down': 'vertical_up',
    'h': 'horizontal'
}

COMMAND = 'scroll-text'

HELP_TXT = 'Scroll text across a matrix.'


def register_command(parser: ArgumentParser):
    scroll_parser = parser.SUBCOMMANDS.add_parser(
        COMMAND,
        help=HELP_TXT
    )

    scroll_parser.add_argument(
        'input',
        type=str,
        help='The text/string that you want to scroll.',
    )

    scroll_parser.add_argument(
        '-d', '--direction',
        type=str,
        choices=DIRECTION_MAP.keys(),
        default='up',
        help='The direction to scroll the text in. Default is up.'
    )

    scroll_parser.add_argument(
        '--sequential',
        action='store_true',
        default=False,
        help=(
            'Treat multiple matrices as a single unified screen. '
            'For horizontal scrolling, the text spans all matrices as one wide canvas. '
            'For vertical scrolling, all matrices display the same animation simultaneously. '
            'Cannot be used with --span-matrices.'
        ),
    )

    scroll_parser.add_argument(
        '--span-matrices',
        action='store_true',
        default=False,
        help='Treat multiple matrices as a single wide canvas when scrolling horizontally. Cannot be used with --sequential.',
    )

    add_matrix_selection_args(scroll_parser)

    return scroll_parser
