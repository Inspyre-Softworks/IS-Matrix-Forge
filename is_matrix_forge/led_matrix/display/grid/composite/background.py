from is_matrix_forge.led_matrix.display.grid.base import Grid


class BackgroundGrid(Grid):
    """Background grid, e.g. for bar fill, patterns, etc."""

    def fill_bar(self, value: int):
        fill_start = max(0, round(self.height - (value / 100) * self.height))
        for x in range(self.width):
            for y in range(fill_start, self.height):
                self._grid[x][y] = 1
