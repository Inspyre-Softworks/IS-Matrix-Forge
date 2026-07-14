from argparse import ArgumentParser

from . import add_matrix_selection_args


COMMAND = "controller-info"

HELP_TXT = (
    "Show detected matrix/controller details, including serial metadata and "
    "firmware version when available."
)


def register_command(parser: ArgumentParser):
    info_parser = parser.SUBCOMMANDS.add_parser(
        COMMAND,
        help=HELP_TXT,
    )

    add_matrix_selection_args(info_parser)
    info_parser.add_argument(
        "--no-firmware",
        action="store_true",
        default=False,
        help="Skip the live firmware version query.",
    )

    return info_parser
