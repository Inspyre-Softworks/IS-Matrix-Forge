from argparse import ArgumentParser


COMMAND = 'show-presets-dir'

HELP_TXT = 'Print the currently configured preset directory path.'


def register_command(parser: ArgumentParser):
    sp_parser = parser.SUBCOMMANDS.add_parser(
        COMMAND,
        help=HELP_TXT,
    )

    return sp_parser
