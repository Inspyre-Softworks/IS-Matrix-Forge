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
from aliaser import alias, Aliases


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

    Parameters
    ----------
    width : int
        Target canvas width (columns).
    height : int
        Target canvas height (rows).
    fill_value : int
        Default pixel value for blank/padded areas (0 or 1).
    init_grid : List[List[int]] | List[int] | None
        Optional initial data. Accepts:
          - column-major 2D list (preferred),
          - row-major 2D list (auto-transposed if shape matches),
          - flat row-major 1D list (e.g., 5×6 glyph).
    align_x : str
        Horizontal placement when `init_grid` is smaller than the canvas.
        One of {'left', 'center', 'right'}. Default: 'center'.
    align_y : str
        Vertical placement when `init_grid` is smaller than the canvas.
        One of {'top', 'center', 'bottom'}. Default: 'center'.
    """

    def __init__(
        self,
        width: int = MATRIX_WIDTH,
        height: int = MATRIX_HEIGHT,
        fill_value: int = 0,
        init_grid: List[List[int]] | List[int] | None = None,
        align_x: str = 'center',
        align_y: str = 'center',
    ) -> None:
        if fill_value not in (0, 1):
            raise ValueError('fill_value must be 0 or 1')

        self._fill_value = fill_value

        # Normalize init_grid to column-major 2D with its *own* intrinsic w×h
        if init_grid is not None:
            src = self._normalize_to_col_major(init_grid, width, height)
            src_w = len(src)
            src_h = len(src[0]) if src else 0
            if width == MATRIX_WIDTH and height == MATRIX_HEIGHT:
                width, height = src_w, src_h
        else:
            src = None
            src_w = width
            src_h = height

        self._width = width
        self._height = height

        # Start with a clean canvas
        canvas = generate_blank_grid(width=width, height=height, fill_value=fill_value)

        if init_grid is None:
            self._grid = canvas
            return

        if src_w == width and src_h == height:
            # Perfect fit: use as-is (defensive copy)
            if not is_valid_grid(src, width, height):
                raise ValueError(f'init_grid must be {width}×{height} column-major 0/1 list')
            self._grid = [col[:] for col in src]
            return

        # Smaller-than-canvas → center (or place per align_x/align_y)
        if src_w <= width and src_h <= height:
            placed = self._place_into_canvas(
                src=src,
                dst_w=width,
                dst_h=height,
                pad_value=fill_value,
                align_x=align_x,
                align_y=align_y,
            )
            if not is_valid_grid(placed, width, height):
                raise ValueError(f'Final grid must be {width}×{height} column-major 0/1 list')
            self._grid = placed
            return

        # Bigger-than-canvas → loud, fast failure (no silent cropping)
        raise ValueError(
            f'init_grid size {src_w}×{src_h} exceeds canvas {width}×{height}. '
            'Resize or supply a proper target width/height.'
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _place_into_canvas(
        src: List[List[int]],
        dst_w: int,
        dst_h: int,
        pad_value: int,
        align_x: str = 'center',
        align_y: str = 'center',
    ) -> List[List[int]]:
        """
        Return a new column-major grid of shape (dst_w×dst_h) with `src` placed
        according to alignment. No cropping; raises if `src` is larger.
        """
        src_w = len(src)
        src_h = len(src[0]) if src else 0

        if src_w > dst_w or src_h > dst_h:
            raise ValueError('Source grid larger than destination canvas.')

        def _off(axis: str, src_len: int, dst_len: int) -> int:
            if axis == 'left' or axis == 'top':
                return 0
            if axis == 'right' or axis == 'bottom':
                return dst_len - src_len
            if axis == 'center':
                return (dst_len - src_len) // 2
            raise ValueError(f'Invalid alignment: {axis}')

        ox = _off(align_x, src_w, dst_w)
        oy = _off(align_y, src_h, dst_h)

        out = generate_blank_grid(width=dst_w, height=dst_h, fill_value=pad_value)
        # Copy pixels
        for x in range(src_w):
            for y in range(src_h):
                out[x + ox][y + oy] = src[x][y]
        return out

    @staticmethod
    def _transpose(matrix: List[List[int]]) -> List[List[int]]:
        return [[row[x] for row in matrix] for x in range(len(matrix[0]))]

    def _normalize_to_col_major(
        self,
        init_grid: List[List[int]] | List[int],
        default_w: int,
        default_h: int,
    ) -> List[List[int]]:
        """
        Accepts:
          - flat row-major 1D (common for 5×6 glyphs),
          - row-major 2D,
          - column-major 2D,
        and returns a column-major 2D grid with its *intrinsic* dimensions.
        """
        # Flat row-major 1D → infer width/height and convert
        if (
            isinstance(init_grid, list)
            and init_grid
            and all(isinstance(v, int) for v in init_grid)
            and not any(isinstance(v, list) for v in init_grid)
        ):
            flat = list(init_grid)
            # If caller used matrix defaults, assume common 5×6 glyph
            w = 5 if (default_w == MATRIX_WIDTH and default_h == MATRIX_HEIGHT) else default_w
            if len(flat) % w != 0:
                raise ValueError(f'Flat init_grid length {len(flat)} not divisible by width {w}')
            h = len(flat) // w
            # row-major → column-major
            return [[flat[r * w + c] for r in range(h)] for c in range(w)]

        # 2D list provided
        if isinstance(init_grid, list) and init_grid and isinstance(init_grid[0], list):
            cand = init_grid
            w = len(cand)
            h = len(cand[0]) if cand else 0
            if w and h:
                if w == default_w and h == default_h:
                    return [col[:] for col in cand]
                if h == default_w and w == default_h:
                    return self._transpose(cand)
                return [col[:] for col in cand]

        raise ValueError('Unsupported init_grid structure; expected 1D flat or 2D list.')

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
