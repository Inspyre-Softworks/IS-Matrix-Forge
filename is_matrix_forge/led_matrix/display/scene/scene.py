from __future__ import annotations
from is_matrix_forge.led_matrix.display.grid import Grid
from is_matrix_forge.led_matrix.display.scene.errors import SceneNotBuiltError


class Scene:
    """
    Scene manager for LED matrix compositing.
    Handles raw background and foreground lists, provides Grid wrappers and composition.
    """

    def __init__(self, background: list, foreground: list = None, invert: bool = True):
        self.__background = background  # raw list of lists (col-major)
        self.__foreground = foreground  # raw list (col-major), or None
        self.invert = invert
        self.__grid = None  # cache for last composed Grid

    @property
    def background(self) -> list:
        """Raw background grid data (col-major list)."""
        return self.__background

    @background.setter
    def background(self, value: list):
        self.__background = value
        self.__grid = None

    @property
    def background_grid(self) -> 'Grid':
        from is_matrix_forge.led_matrix.display.grid.grid import Grid
        return Grid(init_grid=self.__background)

    @property
    def foreground(self) -> list:
        """Raw foreground grid data (col-major list)."""
        return self.__foreground

    @foreground.setter
    def foreground(self, value: list):
        self.__foreground = value
        self.__grid = None

    @property
    def foreground_grid(self) -> 'Grid':
        from is_matrix_forge.led_matrix.display.grid.grid import Grid
        return Grid(init_grid=self.__foreground) if self.__foreground is not None else None

    @property
    def grid(self) -> 'Grid':
        """The composed result as a Grid, or None if not built yet."""
        return self.__grid

    def build(self):
        """
        Compose foreground over background with inversion, cache as __grid.
        Returns a Grid.
        """
        from is_matrix_forge.led_matrix.display.grid.grid import Grid
        bg = self.__background
        fg = self.__foreground
        if bg is None:
            raise ValueError("Scene.background must be set before building")
        width = len(bg)
        height = len(bg[0]) if width else 0
        result = [[0 for _ in range(height)] for _ in range(width)]
        for x in range(width):
            for y in range(height):
                base = bg[x][y]
                if fg and fg[x][y]:
                    result[x][y] = 1 - base if self.invert else fg[x][y]
                else:
                    result[x][y] = base
        self.__grid = Grid(init_grid=result)
        return self.__grid

    def render(self, controller):
        """
        Use a controller to render the composed grid.

        Returns:
            None

        Raises:
            SceneNotBuiltError:
                If scene is not built yet.
        """
        if not self.grid:
            raise SceneNotBuiltError()

        controller.draw_grid(self.grid)

    def __call__(self, controller):
        self.render(controller)
