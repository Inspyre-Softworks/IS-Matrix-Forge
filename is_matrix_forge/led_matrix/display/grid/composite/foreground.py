from is_matrix_forge.led_matrix.display.grid import Grid
from is_matrix_forge.led_matrix.display.assets import DIGITS


class ForegroundGrid(Grid):
    def draw_digits(self, value, bottom_of_grid=False):
        """
        Draw digits on the foreground grid.

        Parameters:
            value (int):
                The value to be displayed.

            bottom_of_grid (bool):
                Whether to draw the digits on the bottom of the grid. Default is False.
        """
        digits = str(value)
        if len(digits) > 2:
            digits = "99"

        digit_w, digit_h, spacing = 3, 5, 1
        total_w = len(digits) * digit_w + (len(digits) - 1) * spacing
        start_x = max((self.width - total_w) // 2, 0)
        digit_y0 = 0 if not bottom_of_grid else self.height - digit_h

        for idx, ch in enumerate(digits):
            self._draw_digit_at(ch, start_x + idx * (digit_w + spacing), digit_y0)

    def _draw_digit_at(self, digit, x0, y0):
        """
        Draw a single digit at a given position.

        Parameters:
            digit (str):
                String representation of the digit to be drawn.

            x0 (int):
                The x-coordinate of the top-left corner of the digit.

            y0 (int):
                The y-coordinate of the top-left
        """
        pattern = DIGITS.get(digit)

        if pattern is None:
            return

        digit_w, digit_h = 3, 5
        for dy in range(digit_h):
            for dx in range(digit_w):
                x, y = x0 + dx, y0 + dy
                if 0 <= x < self.width and 0 <= y < self.height:
                    self._grid[x][y] = pattern[dy][dx]
