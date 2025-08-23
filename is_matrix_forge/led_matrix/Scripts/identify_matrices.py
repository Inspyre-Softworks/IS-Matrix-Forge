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
from typing import List, Optional, Union

from is_matrix_forge.led_matrix.controller import LEDMatrixController
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


class Arguments(ArgumentParser):
    def __init__(self):
        super().__init__('IdentifyLEDMatrices')
        self.__parsed = None

        # Set up the arguments
        self.add_argument(
            '--runtime', '-t',
            action='store',
            default=DEFAULT_RUNTIME,
            help='The total runtime'
        )

        self.add_argument(
            '--skip-clear',
            action='store_true',
            default=False,
            help='Skip clearing LEDs'
        )

        self.add_argument(
            '-c', '--cycle-count',
            action='store',
            type=int,
            default=DEFAULT_CYCLES,
            help='The number of cycles to run per message, for each selected device.'
        )

        # Set up the mutually exclusive arguments for the left and right matrices
        left_right = self.add_mutually_exclusive_group()

        left_right.add_argument(
            '-R', '--only-right',
            action='store_true',
            default=False,
            help='Only display identifying information for/on the rightmost matrix.'
        )

        left_right.add_argument(
            '-L', '--only-left',
            action='store_true',
            default=False,
            help='Only display identifying information for/on the leftmost matrix.'
        )

    @property
    def parsed(self) -> Optional[argparse.Namespace]:
        """
        The parsed arguments (if they've been parsed).

        Returns:
            argparse.Namespace:
                The parsed arguments.

            None:
                If the arguments have not yet been parsed.
        """
        return self.__parsed

    def parse_args(self, *args, **kwargs):
        """
        (Overrides the parent method, since we need to cache the parsed arguments. Does only that and then calls the
        parent method.)

        Parameters:
            *args:
            **kwargs:

        Returns:
            argparse.Namespace:
                The parsed arguments
        """
        self.__parsed = super().parse_args(*args, **kwargs)
        return self.__parsed


def main(
    runtime:     Optional[Union[int, float]] = None,
    only_left:   Optional[bool]              = None,
    only_right:  Optional[bool]              = None,
    skip_clear:  Optional[bool]              = None,
    cycle_count: Optional[int]               = None
):
    """
    The main function of the script.

    Parameters:
        runtime (Optional[Union[int, float]]):
            The total runtime in seconds.

        only_left (Optional[bool]):
            Only display identifying information for/on the leftmost matrix.

        only_right (Optional[bool]):
            Only display identifying information for/on the rightmost matrix.

        skip_clear (Optional[bool]):
            Skip clearing LEDs.

        cycle_count (Optional[int]):
            The number of cycles to run per message, for each selected device.

    Returns:
        List[Thread]:
            A list of threads, one for each LED matrix being identified.
    """
    selected = [LEDMatrixController(device, 100, thread_safe=True) for device in DEVICES]

    if not skip_clear:
        skip_clear = ARGS.parsed.skip_clear

    if only_left is None:
        only_left = ARGS.parsed.only_left

    if only_right is None:
        only_right = ARGS.parsed.only_right

    if only_right:
        selected = [find_rightmost_matrix(selected)]
    elif only_left:
        selected = [find_leftmost_matrix(selected)]

    cycle_count = ARGS.parsed.cycle_count if cycle_count is None else cycle_count

    if runtime is None:
        runtime = ARGS.parsed.runtime

    threads = []

    threads.extend(
        Thread(
            target=device.identify,
            kwargs={
                'skip_clear': skip_clear,
                'duration':   runtime,
                'cycles':     cycle_count
            },
        )
        for device in selected
    )
    for t in threads:
        t.start()

    return threads


ARGS   = Arguments()
PARSED = ARGS.parse_args()

if __name__ == '__main__':
    threads = main()
