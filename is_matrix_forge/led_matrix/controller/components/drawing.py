from __future__ import annotations
from typing import Optional
from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized
from aliaser import alias, Aliases


class DrawingManager(Aliases):
    def __init__(self, *, init_grid=None, show_grid_on_init: bool | None = None,
                 clear_on_init: bool | None = None, **kwargs):
        super().__init__(**kwargs)
        self._grid = None
        self._show_grid_on_init = show_grid_on_init
        self._clear_on_init = clear_on_init

        if init_grid is not None:
            from is_matrix_forge.led_matrix.display.grid import Grid
            if not isinstance(init_grid, Grid):
                raise TypeError(f'init_grid must be Grid, not {type(init_grid)}')
            self._grid = init_grid

        if self.clear_on_init:
            self.clear_matrix()
        if self._grid is not None and self.show_grid_on_init:
            self.draw_grid(self._grid)

    @property
    def grid(self):
        return self._grid

    @property
    def clear_on_init(self) -> Optional[bool]:
        return self._clear_on_init

    @property
    def show_grid_on_init(self) -> Optional[bool]:
        return self._show_grid_on_init

    @alias('clear', 'clear_matrix')
    @synchronized
    def clear_grid(self, fill_value=0) -> None:
        """
        Clears the image from the matrix and redraws the grid to all 0s (by default, to make it all

        Returns:

        """
        from is_matrix_forge.led_matrix.display.grid.helpers import generate_blank_grid
        from is_matrix_forge.led_matrix.display.grid import Grid
        data = generate_blank_grid(fill_value=fill_value)
        self._grid = Grid(init_grid=data)
        self.draw_grid(self._grid)

    @synchronized
    def draw_grid(self, grid: 'Grid' = None) -> None:
        from is_matrix_forge.led_matrix.display.grid import Grid
        from is_matrix_forge.led_matrix.display.helpers import render_matrix
        g = grid or self._grid
        if not isinstance(g, Grid):
            g = Grid(init_grid=g)
        self._grid = g
        render_matrix(self.device, g.grid)

    @synchronized
    def draw_pattern(self, pattern: str) -> None:
        from is_matrix_forge.led_matrix.display.patterns.built_in import BuiltInPatterns
        BuiltInPatterns(self).render(pattern)

    @synchronized
    def show_text(self, text: str) -> None:
        from is_matrix_forge.led_matrix.display.text import show_string
        show_string(self.device, text)

