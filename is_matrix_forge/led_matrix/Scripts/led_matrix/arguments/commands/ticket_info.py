from argparse import ArgumentParser

from . import add_matrix_selection_args


COMMAND = "ticket-info"

HELP_TXT = (
    "Print a support-friendly report for filing a bug ticket, with an option "
    "to copy the full report to the clipboard."
)


def register_command(parser: ArgumentParser):
    ticket_parser = parser.SUBCOMMANDS.add_parser(
        COMMAND,
        help=HELP_TXT,
    )

    add_matrix_selection_args(ticket_parser)
    ticket_parser.add_argument(
        "--copy",
        action="store_true",
        default=False,
        help="Copy the generated ticket report to the clipboard when possible.",
    )
    ticket_parser.add_argument(
        "--copy-format",
        choices=("plain", "markdown"),
        default="plain",
        help="Choose whether copied ticket info should use plaintext or Markdown formatting.",
    )
    ticket_parser.add_argument(
        "--no-firmware",
        action="store_true",
        default=False,
        help="Skip the live firmware version query.",
    )
    ticket_parser.add_argument(
        "--no-update-check",
        action="store_true",
        default=False,
        help="Skip the bounded PyPI update check.",
    )

    return ticket_parser
