"""LED Matrix Controller module."""

from __future__ import annotations

from typing import Optional

from is_matrix_forge.led_matrix.constants import HEIGHT, WIDTH
from is_matrix_forge.led_matrix.display.grid.grid import Grid

from .facade import LEDMatrixController
from .helpers import get_controllers
from .multiton import MultitonMeta
from .threading import synchronized


def generate_blank_grid(width: Optional[int] = None, height: Optional[int] = None) -> Grid:
    return Grid.load_blank_grid(width=width or WIDTH, height=height or HEIGHT)
