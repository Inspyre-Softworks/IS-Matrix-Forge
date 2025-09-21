from argparse import ArgumentParser


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

    return scroll_parser
