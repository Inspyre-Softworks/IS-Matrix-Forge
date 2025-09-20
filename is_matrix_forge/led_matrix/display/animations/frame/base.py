from __future__ import annotations

from threading import Event
from typing import Any, List, Optional, Tuple, Union, Literal

# Local helpers for sleeping/cancel
from .helpers import sleep_with_cancel

from is_matrix_forge.led_matrix.display.grid.base import Grid, MATRIX_WIDTH, MATRIX_HEIGHT


class Frame:
    """
    Represents a single animation frame with a duration.

    Parameters:
        grid (Optional[Union[Grid, List[List[int]], List[int]]], optional):
            Initial grid content. Accepts:
                - `Grid` instance (copied/fit to canvas if needed),
                - column-major 2D list (grid[x][y]),
                - row-major 2D list (auto-transposed if valid),
                - flat row-major 1D list (e.g., 5×6 glyph).
            Defaults to None (blank frame).
        duration (Optional[Union[float, int, str]], optional):
            Frame duration in seconds (non-negative). Strings are cast with `float()`.
            Defaults to `DEFAULT_DURATION`.
        width (Optional[int], optional):
            Target canvas width (columns) when `grid` is not a `Grid`. Defaults to `DEFAULT_WIDTH`.
        height (Optional[int], optional):
            Target canvas height (rows) when `grid` is not a `Grid`. Defaults to `DEFAULT_HEIGHT`.
        fill_value (int, optional):
            Pixel fill used when placing smaller content into the canvas (0 or 1). Defaults to 0.
        align_x (Literal['left','center','right'], optional):
            Horizontal placement for under-sized content. Defaults to 'center'.
        align_y (Literal['top','center','bottom'], optional):
            Vertical placement for under-sized content. Defaults to 'center'.

    Properties:
        grid (Grid):
            The frame's grid content as a `Grid` object.
        duration (float):
            The frame duration in seconds (>= 0).
        width (int):
            Frame canvas width (columns).
        height (int):
            Frame canvas height (rows).
        size (Tuple[int, int]):
            Canvas `(width, height)`.
        number_of_plays (int):
            How many times this frame has been displayed (incremented by `play()`).

    Methods:
        from_dict(data: dict) -> Frame:
            Construct a `Frame` from a dict with keys: 'grid' (required), 'duration' (optional).
        play(device: Any, stop_event: Optional[Event] = None) -> None:
            Draw the frame on `device` and sleep for `duration` (cancellable).

    Raises:
        ValueError:
            If `duration` is invalid/negative; or `grid` content cannot be normalized.
    """

    DEFAULT_DURATION: float = 0.33
    # Mirror Grid defaults so Frame works standalone if Grid constants change later.
    DEFAULT_WIDTH: int = MATRIX_WIDTH
    DEFAULT_HEIGHT: int = MATRIX_HEIGHT

    def __init__(
        self,
        grid: Optional[Union[Grid, List[List[int]], List[int]]] = None,
        duration: Optional[Union[float, int, str]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        *,
        fill_value: int = 0,
        align_x: Literal['left', 'center', 'right'] = 'center',
        align_y: Literal['top', 'center', 'bottom'] = 'center',
    ) -> None:
        # Duration
        self.__duration: float = self._coerce_duration(duration)

        # Target canvas
        target_w: int = width or self.DEFAULT_WIDTH
        target_h: int = height or self.DEFAULT_HEIGHT

        # Establish a baseline Grid to derive fill_value if we need it later
        if grid is None:
            self.__grid: Grid = Grid(width=target_w, height=target_h, fill_value=fill_value)
        elif isinstance(grid, Grid):
            self.__grid = self._fit_grid_to_canvas(
                src=grid,
                dst_w=target_w,
                dst_h=target_h,
                fill_value=fill_value,
                align_x=align_x,
                align_y=align_y,
            )
        else:
            # Raw grid-like → let Grid handle normalization/placement
            self.__grid = Grid(
                width=target_w,
                height=target_h,
                fill_value=fill_value,
                init_grid=grid,
                align_x=align_x,
                align_y=align_y,
            )

        self.__number_of_plays: int = 0

    # ──────────────────────────────────────────────────────────────────────
    # Duration helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _coerce_duration(value: Optional[Union[float, int, str]]) -> float:
        """
        Coerce a duration-like value to a non-negative float, or default.

        Parameters:
            value (Optional[Union[float, int, str]]):
                Duration candidate.

        Returns:
            float:
                Parsed duration (>= 0). Defaults to `DEFAULT_DURATION` if None.

        Raises:
            ValueError:
                If value cannot be parsed to float or is negative.
        """
        if value is None:
            return Frame.DEFAULT_DURATION
        try:
            dur = float(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f'invalid duration: {value!r}') from e
        if dur < 0:
            raise ValueError(f'duration must be non-negative, not {dur}')
        return dur

    # ──────────────────────────────────────────────────────────────────────
    # Grid helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _fit_grid_to_canvas(
        src: Grid,
        dst_w: int,
        dst_h: int,
        fill_value: int,
        align_x: Literal['left', 'center', 'right'],
        align_y: Literal['top', 'center', 'bottom'],
    ) -> Grid:
        """
        Fit an existing `Grid` into a target canvas *without cropping*.

        - If `src` already matches the target size, return a defensive copy.
        - If `src` is smaller, place it per alignment.
        - If `src` is larger, raise (no silent crop).

        Parameters:
            src (Grid):
                Source grid to adapt.
            dst_w (int):
                Target width (columns).
            dst_h (int):
                Target height (rows).
            fill_value (int):
                Pixel fill value for padding (0 or 1).
            align_x (Literal['left','center','right']):
                Horizontal placement.
            align_y (Literal['top','center','bottom']):
                Vertical placement.

        Returns:
            Grid:
                A `Grid` matching `(dst_w, dst_h)` with `src` content.

        Raises:
            ValueError:
                If `src` is larger than destination.
        """
        if src.width == dst_w and src.height == dst_h:
            return Grid(width=dst_w, height=dst_h, fill_value=fill_value, init_grid=src.grid)

        if src.width <= dst_w and src.height <= dst_h:
            placed = Grid._place_into_canvas(
                src=src.grid,
                dst_w=dst_w,
                dst_h=dst_h,
                pad_value=fill_value,
                align_x=align_x,
                align_y=align_y,
            )
            return Grid(width=dst_w, height=dst_h, fill_value=fill_value, init_grid=placed)

        raise ValueError(f'source grid {src.width}×{src.height} exceeds target {dst_w}×{dst_h}')

    # ──────────────────────────────────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────────────────────────────────

    @property
    def duration(self) -> float:
        """
        The time to wait after displaying this frame before moving to the next.

        Returns:
            float:
                Frame duration in seconds (>= 0). Defaults to `DEFAULT_DURATION` if unset.
        """
        return self.__duration

    @duration.setter
    def duration(self, new: Union[float, int, str]) -> None:
        """
        Set the duration of the frame.

        Parameters:
            new (Union[float, int, str]):
                Duration in seconds (non-negative). Strings are cast with `float()`.

        Raises:
            ValueError:
                If `new` cannot be parsed or is negative.
        """
        self.__duration = self._coerce_duration(new)

    @property
    def grid(self) -> Grid:
        """
        The frame content as a `Grid` object.

        Returns:
            Grid:
                A `Grid` representing this frame.
        """
        return self.__grid

    @grid.setter
    def grid(self, value: Union[Grid, List[List[int]], List[int]]) -> None:
        """
        Replace the frame's grid content.

        Parameters:
            value (Union[Grid, List[List[int]], List[int]]):
                New grid content. If a `Grid` is provided, it is adopted (and fit to current canvas);
                if a raw list is provided, it is normalized into the current canvas using `Grid`.

        Raises:
            ValueError:
                If provided content cannot be normalized/validated.
        """
        if isinstance(value, Grid):
            self.__grid = self._fit_grid_to_canvas(
                src=value,
                dst_w=self.width,
                dst_h=self.height,
                fill_value=self.__grid.fill_value if hasattr(self, '_Frame__grid') else 0,
                align_x='center',
                align_y='center',
            )
            return

        # Normalize raw into our current canvas
        self.__grid = Grid(
            width=self.width,
            height=self.height,
            fill_value=self.__grid.fill_value if hasattr(self, '_Frame__grid') else 0,
            init_grid=value,
            align_x='center',
            align_y='center',
        )

    @property
    def width(self) -> int:
        """
        Frame canvas width (columns).

        Returns:
            int:
                Number of columns.
        """
        return self.__grid.width

    @property
    def height(self) -> int:
        """
        Frame canvas height (rows).

        Returns:
            int:
                Number of rows.
        """
        return self.__grid.height

    @property
    def size(self) -> Tuple[int, int]:
        """
        The dimensions of the grid.

        Returns:
            Tuple[int, int]:
                `(width, height)`.
        """
        return self.width, self.height

    @property
    def number_of_plays(self) -> int:
        """
        How many times this frame has been displayed.

        Returns:
            int:
                Count of `play()` calls completed.
        """
        return self.__number_of_plays

    @number_of_plays.setter
    def number_of_plays(self, new: int) -> None:
        """
        Set the number of times this frame has been displayed.

        Parameters:
            new (int):
                Non-negative integer.

        Raises:
            ValueError:
                If `new` is not a non-negative integer.
        """
        if not isinstance(new, int) or new < 0:
            raise ValueError('number_of_plays must be a non-negative integer')
        self.__number_of_plays = new

    # ──────────────────────────────────────────────────────────────────────
    # Factory & runtime
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def from_dict(data: dict) -> 'Frame':
        """
        Create a `Frame` object from a formatted dictionary.

        Parameters:
            data (dict):
                Dictionary with:
                    - 'grid' (required): grid-like content,
                    - 'duration' (optional): seconds,
                    - 'width' (optional): columns,
                    - 'height' (optional): rows.

        Returns:
            Frame:
                A new `Frame` object.

        Raises:
            KeyError:
                If 'grid' is missing.
            ValueError:
                If 'duration' is invalid.
        """
        if 'grid' not in data:
            raise KeyError("missing required key 'grid'")
        return Frame(
            grid=data['grid'],
            duration=data.get('duration', Frame.DEFAULT_DURATION),
            width=data.get('width'),
            height=data.get('height'),
        )

    def play(self, device: Any, stop_event: Optional[Event] = None) -> None:
        """
        Play the frame on the LED matrix device.

        Parameters:
            device (Any):
                An object exposing `draw_grid(Grid)`.
            stop_event (Optional[Event], optional):
                If provided, sleep will be cancellable via this event.

        Raises:
            AttributeError:
                If `device.draw_grid` is missing or not callable.
        """
        if not hasattr(device, 'draw_grid') or not callable(device.draw_grid):
            raise AttributeError('device.draw_grid(grid) not available')

        device.draw_grid(self.grid)

        try:
            sleep_with_cancel(self.duration, stop_event)
        except Exception:
            # Fallback if helper import/behavior fails
            import time
            if stop_event is None:
                time.sleep(self.duration)
            else:
                remaining = self.duration
                step = 0.02
                while remaining > 0 and not stop_event.is_set():
                    time.sleep(min(step, remaining))
                    remaining -= step

        self.__number_of_plays += 1

    # ──────────────────────────────────────────────────────────────────────
    # Dunder
    # ──────────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f'Frame(size={self.size}, duration={self.duration:.3f}s, plays={self.number_of_plays})'

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Frame):
            return False
        return self.grid == other.grid and self.duration == other.duration

    def __hash__(self) -> int:
        return hash((self.grid, self.duration))

    def __copy__(self) -> 'Frame':
        return Frame(
            grid=self.grid,
            duration=self.duration,
            width=self.width,
            height=self.height,
        )
