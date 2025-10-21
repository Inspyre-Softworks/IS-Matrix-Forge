from argparse import ArgumentParser


COMMAND = 'display-text'


HELP_TXT = 'Display a static string on the matrix until interrupted.'


def register_command(parser: ArgumentParser):
    display_parser = parser.SUBCOMMANDS.add_parser(
        COMMAND,
        help=HELP_TXT,
    )

    display_parser.add_argument(
        'text',
        type=str,
        help='The text/string that you want to display.',
    )

    display_parser.add_argument(
        '--run-for',
        type=float,
        default=None,
        metavar='SECONDS',
        help='Automatically stop after the specified number of seconds. Defaults to running until interrupted.',
    )

    display_parser.add_argument(
        '--skip-clear',
        action='store_true',
        default=False,
        help='Do not clear the matrix after the display stops.',
    )

    return display_parser
