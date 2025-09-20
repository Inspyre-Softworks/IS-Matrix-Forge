from typing import List, Union
from is_matrix_forge.led_matrix.display.grid.base import Grid
from inspyre_toolbox.syntactic_sweets.classes.decorators import validate_type


def transpose(grid):
    return [[row[x] for row in grid] for x in range(len(grid[0]))]


def load_grid(grid_list):
    if not isinstance(grid_list, list):
        if isinstance(grid_list, Grid):
            return grid_list
        raise ValueError(f"grid_list must be a list of lists not {type(grid_list)}")

    try:
        return Grid(init_grid=grid_list)
    except ValueError as e:
        msg = str(e)
        if msg.startswith('ValueError: init_grid must be'):
            print('caught a ValueError: init_grid must be a list of lists')
            return Grid(init_grid=transpose(grid_list))
        raise e from e


class CompositeGrid(Grid):
    """
    CompositeGrid: overlays a single foreground Grid on top of a background Grid.

    - Optionally inverts background pixels where both foreground and background are 'on'.

    Properties:
        background (Grid): Background grid
        foreground (Grid): Foreground grid
        invert_on_overlap (bool): If True, inverts on pixel overlaps
    """
    def __init__(
        self,
        background: Union[Grid, List[List[int]]],
        foreground: Union[Grid, List[List[int]]],
        invert_on_overlap: bool = False
    ):
        self.__background = background
        self.__foreground = foreground
        self.__invert_on_overlap = invert_on_overlap

    @property
    def background(self) -> Grid:
        return self.__background

    @background.setter
    def background(self, bg: Union[Grid, List[List[int]]]):
        self.__background = load_grid(bg)

    @property
    def foreground(self) -> Grid:
        return self.__foreground

    @foreground.setter
    def foreground(self, fg: Union[Grid, List[List[int]]]):
        self.__foreground = load_grid(fg)

    @property
    def invert_on_overlap(self) -> bool:
        return self.__invert_on_overlap

    @invert_on_overlap.setter
    @validate_type(bool)
    def invert_on_overlap(self, val):
        self.__invert_on_overlap = val

    def render(self) -> Grid:
        """
        Build and return a composite Grid with foreground drawn over background.
        Pixels where both background and foreground are 'on' are optionally inverted.
        """
        base = self.background.copy()
        fg = self.foreground

        for y in range(base.height):
            for x in range(base.width):
                if (fg_val := fg._grid[x][y]):
                    bg_val = base._grid[x][y]
                    base._grid[x][y] = 0 if self.invert_on_overlap and bg_val else fg_val

        return base

    def draw(self, device) -> None:
        """Render and draw to device."""
        grid_to_draw = self.render()
        device.draw_grid(grid_to_draw)
