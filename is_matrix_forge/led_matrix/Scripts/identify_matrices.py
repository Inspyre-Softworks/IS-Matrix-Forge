"""
The main entrypoint for the `led-matrix-identify` command.

Description:
    This module contains the entrypoint for the `led-matrix-identify` command, which
    is used to identify:

        * Which LED matrix can be communicated with by which serial port
        * The physical location of each LED matrix


See `main()` for more information.

Author:
    Taylor B. <t.blackstone@inspyre.tech>

Since:
    v1.0.0
"""
import argparse
from argparse import ArgumentParser
from typing import Optional

from is_matrix_forge.led_matrix.Scripts.led_matrix import identify_matrices_command


DEFAULT_RUNTIME = 30
DEFAULT_CYCLES  = 3


def build_parser() -> ArgumentParser:
    parser = ArgumentParser('IdentifyLEDMatrices')

    parser.add_argument(
        '--runtime', '-t',
        action='store',
        type=float,
        default=float(DEFAULT_RUNTIME),
        help='The total runtime in seconds.',
    )

    parser.add_argument(
        '--skip-clear',
        action='store_true',
        default=False,
        help='Skip clearing LEDs.',
    )

    parser.add_argument(
        '-c', '--cycle-count',
        action='store',
        type=int,
        default=DEFAULT_CYCLES,
        help='The number of cycles to run per message, for each selected device.',
    )

    left_right = parser.add_mutually_exclusive_group()
    left_right.add_argument(
        '-R', '--only-right',
        action='store_true',
        default=False,
        help='Only display identifying information for/on the rightmost matrix.',
    )

    left_right.add_argument(
        '-L', '--only-left',
        action='store_true',
        default=False,
        help='Only display identifying information for/on the leftmost matrix.',
    )

    return parser


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    return build_parser().parse_args(args=args)


def main(arguments: argparse.Namespace) -> None:
    """Execute the identification routine based on parsed arguments.

    Delegates to the shared ``identify-matrices`` command so the legacy script
    mirrors the CLI behaviour without duplicating controller management logic.
    """

    identify_matrices_command(arguments)


def run_from_cli(args: Optional[list[str]] = None) -> None:
    return main(parse_args(args=args))


if __name__ == '__main__':
    run_from_cli()
