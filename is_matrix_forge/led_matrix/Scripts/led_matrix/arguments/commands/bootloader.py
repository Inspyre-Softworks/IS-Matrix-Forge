from argparse import ArgumentParser

from . import add_matrix_selection_args


COMMAND = 'bootloader'

HELP_TXT = (
    'Reboot the selected matrix into its firmware bootloader. '
    'The device will disconnect from the OS until it is reflashed or power-cycled.'
)


def register_command(parser: ArgumentParser):
    bl_parser = parser.SUBCOMMANDS.add_parser(
        COMMAND,
        help=HELP_TXT,
    )

    add_matrix_selection_args(bl_parser)

    return bl_parser
