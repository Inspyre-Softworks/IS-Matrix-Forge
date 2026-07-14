from argparse import ArgumentParser


COMMAND = 'set-presets-dir'

HELP_TXT = (
    'Change the directory where presets are stored. '
    'Existing preset files are moved to the new location automatically '
    'and the setting is saved to settings.json.'
)


def register_command(parser: ArgumentParser):
    sp_parser = parser.SUBCOMMANDS.add_parser(
        COMMAND,
        help=HELP_TXT,
    )

    sp_parser.add_argument(
        'path',
        type=str,
        help='Absolute path to the new presets directory.',
    )

    return sp_parser
