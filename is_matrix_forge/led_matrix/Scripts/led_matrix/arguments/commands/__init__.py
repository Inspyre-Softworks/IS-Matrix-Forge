"""


Author: 
    Inspyre Softworks

Project:
    IS-Matrix-Forge

File: 
    is_matrix_forge/led_matrix/Scripts/led_matrix/arguments/commands/__init__.py
 

Description:
    Shared helpers for subcommand argument parsers.

"""
from argparse import ArgumentParser


def add_matrix_selection_args(parser: ArgumentParser) -> None:
    """Add ``-L``/``-R`` matrix-selection flags to a subcommand parser.

    Mirrors the top-level ``led-matrix`` flags so that users can place
    ``--only-left`` / ``--only-right`` either before *or* after the
    subcommand name on the command line.

    Argparse only writes a subparser's default value for a ``dest`` that is
    not already present in the namespace, so the parent's explicit ``-L``/
    ``-R`` values are never overwritten when the flag appears before the
    subcommand.  When the flag appears after the subcommand name the
    subparser processes it directly and sets the correct value.
    """
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-L', '--only-left',
        action='store_true',
        help='Only target the leftmost matrix.',
    )
    group.add_argument(
        '-R', '--only-right',
        action='store_true',
        help='Only target the rightmost matrix.',
    )
