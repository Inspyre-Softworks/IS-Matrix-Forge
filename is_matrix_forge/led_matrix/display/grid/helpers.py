from __future__ import annotations

import threading
from typing import Any, List

try:
    from inspyre_toolbox.chrono import sleep as ist_sleep
except ModuleNotFoundError:  # pragma: no cover - fallback when dependency missing
    from time import sleep as ist_sleep
from serial.tools.list_ports_common import ListPortInfo

from is_matrix_forge.common.helpers import coerce_to_int
from is_matrix_forge.led_matrix.helpers.device import get_devices
from is_matrix_forge.led_matrix.constants import HEIGHT, WIDTH
from is_matrix_forge.led_matrix.display.helpers import render_matrix
from is_matrix_forge.led_matrix.errors import MalformedGridError


def get_grid_spec_from_animation_file(path: str, frame_number: int) -> List[List[int]]:
    pass


def generate_blank_grid(
        width: int = WIDTH,
        height: int = HEIGHT,
        fill_value: int = 0
) -> List[List[int]]:
    """
    Generate a blank grid of the specified width and height.

    A blank grid is a list of lists of 0s, where each inner list represents a row of the grid.

    Parameters:
        width (int):
            The width (in pixels) of the grid. Default is 9.

        height (int):
            The height (in pixels) of the grid. Default is 34.

        fill_value (int):
            The value to fill the grid with:

              - Default is 0.
              - Accepts 0 or 1:
                  - 0 for no LEDs on.
                  - 1 for all LEDs on.

    Returns:
        List[List[int]]:
            A blank grid of the specified width and height.

    Raises:
        TypeError:
            If width or height is not an int.
    """
    if not isinstance(width, int):
        width = coerce_to_int(width)
        if width is None:
            raise TypeError(f"width must be an int, not {type(width)}")

    if not isinstance(height, int):
        height = coerce_to_int(height)
        if height is None:
            raise TypeError(f"height must be an int, not {type(height)}")

    if not isinstance(fill_value, int):
        fill_value = coerce_to_int(fill_value)
        if fill_value is None:
            raise TypeError(f"fill_value must be an int, not {type(fill_value)}")

    if fill_value not in (0, 1):
        raise ValueError(f"fill_value must be 0 or 1, not {fill_value}")

    return [
        [fill_value for _ in range(height)]
        for _ in range(width)
    ]


def is_valid_grid(grid, width, height):

    # column-major: width columns of height rows each
    return (
        isinstance(grid, list)
        and len(grid) == width
        and all(
            isinstance(col, list)
            and len(col) == height
            and all(cell in (0,1) for cell in col)
            for col in grid
        )
    )




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

    def worker(interval):
        global running
        running.state = True
        while running:
            ist_sleep(interval)
            render_matrix(dev, grid)

    thread = threading.Thread(target=worker, args=(reapply_interval,), daemon=True)
    thread.start()
