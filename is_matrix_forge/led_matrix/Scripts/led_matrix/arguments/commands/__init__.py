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
import argparse
from argparse import ArgumentParser


def add_matrix_selection_args(parser: ArgumentParser) -> None:
    """Add ``-L``/``-R`` matrix-selection flags to a subcommand parser.

    Mirrors the top-level ``led-matrix`` flags so that users can place
    ``--only-left`` / ``--only-right`` either before *or* after the
    subcommand name on the command line.

    ``default=argparse.SUPPRESS`` is used on the subparser flags so that
    when neither flag is passed after the subcommand, the attribute is absent
    from the subparser's fresh namespace.  Python 3.12 merges all subparser
    namespace values back onto the parent namespace unconditionally, so using
    ``SUPPRESS`` ensures a default ``False`` from the subparser never
    overwrites a ``True`` that was set by the parent parser when the flag
    appeared before the subcommand name.
    """
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-L', '--only-left',
        action='store_true',
        default=argparse.SUPPRESS,
        help='Only target the leftmost matrix.',
    )
    group.add_argument(
        '-R', '--only-right',
        action='store_true',
        default=argparse.SUPPRESS,
        help='Only target the rightmost matrix.',
    )
