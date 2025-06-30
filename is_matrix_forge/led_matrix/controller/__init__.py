"""
LED Matrix Controller Module.

This module provides the main controller class for interacting with LED matrix devices.
It handles device communication, animation control, pattern display, and other
operations related to the LED matrix hardware.
"""

from __future__ import annotations

# Standard library
from typing import Optional

# Third‑party

# Inspyre‑Softworks

from .multiton import MultitonMeta
from is_matrix_forge.led_matrix.constants import HEIGHT, WIDTH

from is_matrix_forge.led_matrix.display.grid.grid import Grid
from .helpers.threading import synchronized
from .controller import LEDMatrixController
from .helpers import get_controllers


def generate_blank_grid(width: Optional[int] = None, height: Optional[int] = None) -> Grid:
    return Grid.load_blank_grid(width=width or WIDTH, height=height or HEIGHT)
