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
from threading import Thread
from typing import List, Optional

from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
from is_matrix_forge.led_matrix.constants import DEVICES


DEFAULT_RUNTIME = 30
DEFAULT_CYCLES  = 3


def find_leftmost_matrix(matrices: List[LEDMatrixController]) -> Optional[LEDMatrixController]:
    """
    Determine the leftmost (physically) LED matrix.

    Parameters:
        matrices (List[LEDMatrixController]):
            The controller objects for all LED matrices.

    Returns:
        Optional[LEDMatrixController]:
            The controller object representing the determined leftmost matrix, `None`
            if none found.
    """
    if left_devices := [m for m in matrices if m.side_of_keyboard == 'left']:
        return min(left_devices, key=lambda m: m.slot)

    # Fallback: use right-side devices if no left-side
    right_devices = [m for m in matrices if m.side_of_keyboard == 'right']

    return min(right_devices, key=lambda m: m.slot) if right_devices else None


def find_rightmost_matrix(matrices: List[LEDMatrixController]) -> Optional[LEDMatrixController]:
    """
    Determine the rightmost (physically) LED matrix.

    Parameters:
        matrices (List[LEDMatrixController]):
            The controller objects for alll LED matrices.

    Returns:
        Optional[LEDMatrixController]:
            The controller object representing the determined rightmost matrix, `None`
            if none found.
    """

    if right_devices := [m for m in matrices if m.side_of_keyboard == 'right']:
        return max(right_devices, key=lambda m: m.slot)

    # Fallback: use left-side devices if no right-side
    left_devices = [m for m in matrices if m.side_of_keyboard == 'left']

    return max(left_devices, key=lambda m: m.slot) if left_devices else None


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


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    return build_parser().parse_args(args=args)


def main(arguments: argparse.Namespace) -> List[Thread]:
    """Execute the identification routine based on parsed arguments."""

    selected = [LEDMatrixController(device, 100, thread_safe=True) for device in DEVICES]

    if arguments.only_right:
        selected = [device for device in [find_rightmost_matrix(selected)] if device]
        if not selected:
            print("Error: No rightmost matrix found in the selection.")
            return
    elif arguments.only_left:
        selected = [device for device in [find_leftmost_matrix(selected)] if device]
        if not selected:
            print("Error: No leftmost matrix found in the selection.")
            return

    threads = [
        Thread(
            target=device.identify,
            kwargs={
                'skip_clear': arguments.skip_clear,
                'duration':   arguments.runtime,
                'cycles':     arguments.cycle_count,
            },
        )
        for device in selected
    ]

    for thread in threads:
        thread.start()

    return threads


def run_from_cli(args: Optional[List[str]] = None) -> List[Thread]:
    return main(parse_args(args=args))


if __name__ == '__main__':
    run_from_cli()
