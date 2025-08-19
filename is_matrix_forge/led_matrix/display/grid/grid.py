# is_matrix_forge.led_matrix.display.grid.grid
"""
Grid module for LED Matrix display.

Author: 
    Inspyre Softworks

Project:
    led-matrix-battery

File: 
    is_matrix_forge/led_matrix/display/grid/grid.py

Description:
    This module provides the Grid class which represents a 2D grid of pixels
    for the LED matrix display. It handles grid creation, manipulation, and
    loading from files.
"""

import itertools
from pathlib import Path
from typing import List, Optional, Union, ClassVar, Type, Any, Dict  # Added Any, Dict
from ...constants import WIDTH as __WIDTH, HEIGHT as __HEIGHT, PRESETS_DIR
from .helpers import is_valid_grid, generate_blank_grid
from ...helpers import load_from_file as _helpers_load_from_file
from is_matrix_forge.common.helpers import coerce_to_int

MATRIX_HEIGHT = 34
"""int: Height of the LED matrix grid in pixels.
This constant defines the default height for new Grid instances and for loading operations.
"""

MATRIX_WIDTH = 9
"""int: Width of the LED matrix grid in pixels.
This constant defines the default width for new Grid instances and for loading operations.
"""


def load_from_file(
    path: Union[str, Path],
    expected_width: Optional[int] | None = MATRIX_WIDTH,
    expected_height: Optional[int] | None = MATRIX_HEIGHT,
    fallback_duration: Optional[Union[int, float]] = None,
) -> Any:
    """Wrapper around :func:`is_matrix_forge.led_matrix.helpers.load_from_file`.

    Exists primarily for unit tests which monkeypatch this function directly.
    """
    return _helpers_load_from_file(
        path,
        expected_width,
        expected_height,
        fallback_duration,
    )


class Grid:
    """
    Represents a 2D column-major grid for the LED display (grid[x][y], 9×34).
    Provides methods for grid creation, manipulation, and loading from files.

    The Grid class allows for the management of pixel data in a column-major format,
    supporting operations such as shifting, drawing, and loading from specifications or files.
    """

    def __init__(
        self,
        width: int = MATRIX_WIDTH,
        height: int = MATRIX_HEIGHT,
        fill_value: int = 0,
        init_grid: List[List[int]] = None
    ) -> None:
        """
        Initialize a Grid. If `init_grid` is provided, it must be column-major
        with shape (width × height). Otherwise, create a blank grid.
        """
        self._grid = []
        if init_grid is not None:
            # Accept a flat list (row-major) or a list of lists. If the user
            # provides a flattened 5×6 glyph (as returned by
            # ``convert_symbol``/``convert_font``), attempt to infer the
            # dimensions and convert it to the column‑major format used by the
            # Grid class.
            if (
                isinstance(init_grid, list)
                and init_grid
                and all(isinstance(v, int) for v in init_grid)
                and not any(isinstance(v, list) for v in init_grid)
            ):
                flat = list(init_grid)
                # If the caller didn't specify dimensions (i.e. left the
                # defaults of 9×34) assume a 5×6 font glyph which is the
                # primary flat list used throughout the project.
                if width == MATRIX_WIDTH and height == MATRIX_HEIGHT:
                    width = 5
                    height = len(flat) // width
                if len(flat) != width * height:
                    raise ValueError(
                        f"Flat init_grid length {len(flat)} does not match {width}×{height}"
                    )
                # Convert from row-major 1D list to column-major list of
                # lists.
                init_grid = [
                    [flat[r * width + c] for r in range(height)] for c in range(width)
                ]
            else:
                # Try to detect if row-major 2D was given by mistake. First
                # check if the provided grid is already valid column-major. If
                # not, attempt a transpose and validate again.
                if isinstance(init_grid, list) and init_grid and isinstance(init_grid[0], list) and (not is_valid_grid(init_grid, width, height) and len(init_grid) == height and len(init_grid[0]) == width):
                    transposed = [[row[x] for row in init_grid] for x in range(width)]
                    if is_valid_grid(transposed, width, height):
                        init_grid = transposed

                    

            if not is_valid_grid(init_grid, width, height):
                raise ValueError(
                    f"init_grid must be {width}×{height} column-major 0/1 list"
                )
            self._grid = [col[:] for col in init_grid]
        else:
            if fill_value not in (0, 1):
                raise ValueError("fill_value must be 0 or 1")
            self._grid = generate_blank_grid(
                width=width, height=height, fill_value=fill_value
            )

        self._width = width
        self._height = height
        self._fill_value = fill_value

    @property
    def grid(self) -> List[List[int]]:
        """Defensive copy of the column-major grid data."""
        return [col[:] for col in self._grid]

    @grid.setter
    def grid(self, value: List[List[int]]) -> None:
        """Replace the internal grid; must be column-major and correct shape."""
        if not is_valid_grid(value, self._width, self._height):
            raise ValueError(f"grid must be {self._width}×{self._height} column-major 0/1 list")
        self._grid = [col[:] for col in value]

    @property
    def width(self) -> int:
        """Number of columns."""
        return self._width

    @property
    def height(self) -> int:
        """Number of rows."""
        return self._height

    @property
    def fill_value(self) -> int:
        """Default pixel fill (0 or 1)."""
        return self._fill_value

    @fill_value.setter
    def fill_value(self, v: int) -> None:
        """Set default pixel fill; must be 0 or 1."""
        if not isinstance(v, int) or v not in (0, 1):
            raise ValueError("fill_value must be 0 or 1")
        self._fill_value = v

    @property
    def cols(self) -> int:
        """Alias for width."""
        return self._width

    @property
    def rows(self) -> int:
        """Alias for height."""
        return self._height

    @classmethod
    def load_blank_grid(
        cls,
        width:      int = MATRIX_WIDTH,
        height:     int = MATRIX_HEIGHT,
        fill_value: int = 0
    ) -> List[List[int]]:
        """Return a new blank column-major grid."""
        return generate_blank_grid(width=width, height=height, fill_value=fill_value)

    @classmethod
    def from_spec(
        cls,
        spec: List[List[int]]
    ) -> 'Grid':
        """Instantiate directly from a column-major spec list.

        The dimensions of the grid are inferred from ``spec`` so tests can
        provide arbitrary sized grids.
        """
        width = len(spec)
        height = len(spec[0]) if spec else 0
        if not is_valid_grid(spec, width, height):
            raise ValueError(
                f"init_grid must be {width}×{height} column-major 0/1 list"
            )
        return cls(width=width, height=height, init_grid=spec)

    @classmethod
    def from_file(
        cls,
        filename: Union[str, Path],
        frame_number: int = 0,
        height: int = MATRIX_HEIGHT,
        width: int = MATRIX_WIDTH
    ) -> 'Grid':
        """
        Load a column-major grid from file (single grid or frames of grids).
        """
        raw = load_from_file(str(filename))
        # Single-grid JSON: list of lists
        if (
            isinstance(raw, list)
            and raw
            and isinstance(raw[0], list)
            and is_valid_grid(raw[0], width, height)
        ):
            grid_data = raw[0]
        elif isinstance(raw, list) and raw and isinstance(raw[0], list):
            grid_data = raw
        # Frame-list JSON: list of dicts
        elif isinstance(raw, list) and all(isinstance(f, dict) for f in raw):
            frame = raw[frame_number]
            grid_data = frame.get('grid')
            if not isinstance(grid_data, list):
                raise ValueError(f"Frame {frame_number} missing 'grid' list")
        else:
            raise ValueError("Unsupported file structure for grid data.")

        if not is_valid_grid(grid_data, width, height):
            raise ValueError(f"Loaded grid is not {width}×{height} column-major 0/1 list")

        return cls(width=width, height=height, init_grid=grid_data)

    def copy(self) -> "Grid":
        """
        Return a new `Grid` object with a deep copy of the grid data and same parameters.
        """
        return Grid(
            width=self.width,
            height=self.height,
            fill_value=self.fill_value,
            init_grid=[col[:] for col in self.grid]
        )

    def draw(self, device: Any) -> None:
        """Draw this grid via device.draw_grid(grid)."""
        if not hasattr(device, 'draw_grid') or not callable(device.draw_grid):
            raise AttributeError("device.draw_grid(grid) not available")
        device.draw_grid(self)

    def get_pixel_value(self, x: int, y: int) -> int:
        """Return the value at column x, row y."""
        if x < 0 or x >= self._width or y < 0 or y >= self._height:
            raise IndexError(f"({x},{y}) out of bounds {self._width}×{self._height}")
        return self._grid[x][y]

    def get_shifted(
        self,
        dx: int = 0,
        dy: int = 0,
        wrap: bool = False
    ) -> 'Grid':
        """
        Return a new Grid shifted by (dx, dy):
          - dx > 0 moves right, dx < 0 moves left
          - dy > 0 moves down, dy < 0 moves up
        If wrap=True, shifts wrap around edges; otherwise, out-of-bounds fill with fill_value.
        """
        new = generate_blank_grid(self._width, self._height, self._fill_value)

        for c, r in itertools.product(range(self._width), range(self._height)):
            dest_c = (c + dx) % self._width if wrap else c + dx
            dest_r = (r + dy) % self._height if wrap else r + dy

            if 0 <= dest_c < self._width and 0 <= dest_r < self._height:
                new[dest_c][dest_r] = self._grid[c][r]

        return self.__class__(width=self._width, height=self._height, fill_value=self._fill_value, init_grid=new)

    def __getitem__(self, index: int) -> list[int]:
        """Allow column-major indexing: grid[col] → list of pixel values down that column."""
        return self._grid[index]

    def __len__(self) -> int:
        """Number of columns (i.e. grid width)."""
        return len(self._grid)

    def __iter__(self):
        """Iterate over columns."""
        return iter(self._grid)
