from typing import List
from .base import Frame
from serial.tools.list_ports_common import ListPortInfo
from is_matrix_forge.led_matrix.display.grid.helpers import is_valid_grid
from is_matrix_forge.led_matrix.display.animations.errors import MalformedGridError
from is_matrix_forge.led_matrix.display.helpers import render_matrix


running = False


def hold_pattern(dev, grid: List[List[int]], reapply_interval: float = 55.00) -> None:
    """
    Hold the state of the LED matrix indefinitely, only updating the display every `reapply_interval` seconds.

    This is useful for maintaining a static display on the LED matrix without having a constant refresh/computation
    load.

    Parameters:
        dev (ListPortInfo):
            The serial com device/port to use.

        grid (List[List[int]])::
            The grid to display on the LED matrix.

        reapply_interval (Union[float, int]):
            The interval in seconds at which to reapply the grid state to the LED matrix. Default is 55 seconds,
            maximum is 60 (the number of seconds before the matrix turns all the LEDs off unless a new state is
            applied)

    Returns:
        None
    """

    if not isinstance(dev, ListPortInfo):
        raise TypeError(f"dev must be a ListPortInfo object, not {type(dev)}")

    if not isinstance(grid, list) or not is_valid_grid(grid, 9, 34):
        raise MalformedGridError(f"grid must be a 9x34 list of 0/1, not {type(grid)}")

    cycles = 0
    def worker(interval):
        global running, cycles
        running = True
        while running:
            cycles += 1
            render_matrix(dev, grid)
