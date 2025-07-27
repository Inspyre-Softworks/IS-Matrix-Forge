"""


Author: 
    Inspyre Softworks

Project:
    led-matrix-battery

File: 
    ${DIR_PATH}/${FILE_NAME}
 

Description:
    $DESCRIPTION

"""
from typing import List



class TextScroller:
    """
    Generate Frame objects for scrolling text bottom-to-top on an LED matrix.

    Frames are returned as a list of "columns", each column is a list of bits down the rows.
    """

    def __init__(
        self,
        font,
        rows: int = 34,
        cols: int = 9,
        delay: float = 0.1,
        letter_width: int = 5,
        letter_height: int = 6,
        spacing: int = 1,
        col_offset: int = 2,
    ):
        """
        Initialize a TextScroller.

        Parameters:
            font:
                A font object with convert_font(char) -> glyph callable.
            rows:
                Number of rows in the matrix.
            cols:
                Number of columns in the matrix.
            delay:
                Duration for each generated Frame.
            letter_width:
                Width of each character in pixels.
            letter_height:
                Height of each character in pixels.
            spacing:
                Vertical spacing between characters.
            col_offset:
                Horizontal offset for character placement.
        """
        self.font = font
        self.rows = rows
        self.cols = cols
        self.delay = delay
        self.letter_width = letter_width
        self.letter_height = letter_height
        self.spacing = spacing
        self.col_offset = col_offset

    def scroll(self, text: str, skip_end_space: bool = False) -> List['Frame']:
        """
        Build and return a list of Frame objects representing the text scroll.

        Parameters:
            text:
                The text string to scroll.
            skip_end_space:
                If True, omit trailing blank frames after text.

        Returns:
            A list of Frame instances, each covering the full matrix as columns×rows.
        """
        from is_matrix_forge.led_matrix.display.animations.frame import Frame

        grid = self._build_big_grid(text)
        total_height = len(grid)
        end_limit = total_height if skip_end_space else total_height + self.rows
        frames: List[Frame] = []

        for top in range(-self.rows, end_limit):
            # extract a rows×cols slice (list of rows)
            slice_rows = [
                grid[r] if 0 <= r < total_height else [0] * self.cols
                for r in range(top, top + self.rows)
            ]
            # reorient to columns×rows
            cols_grid = self._orient_frame(slice_rows)
            frames.append(Frame(cols_grid, duration=self.delay))

        return frames

    def _build_big_grid(self, text: str) -> List[List[int]]:
        """
        Build a concatenated vertical grid of all glyphs in text as list of rows.

        Returns:
            A 2D list of bits [total_height][cols].
        """
        font_items = [self.font.convert_font(c) for c in text]
        total_height = len(font_items) * (self.letter_height + self.spacing) - self.spacing
        grid = [[0] * self.cols for _ in range(total_height)]

        for idx, glyph in enumerate(font_items):
            base = idx * (self.letter_height + self.spacing)
            for x in range(self.letter_width):
                for y in range(self.letter_height):
                    if glyph[x + y * self.letter_width]:
                        grid[base + y][self.col_offset + x] = 1

        return grid

    def _orient_frame(self, rows_grid: List[List[int]]) -> List[List[int]]:
        """
        Transpose a rows×cols grid into cols×rows orientation.

        Parameters:
            rows_grid:
                A list of self.rows lists, each length self.cols.

        Returns:
            A list of self.cols lists, each length self.rows.
        """
        return [
            [rows_grid[r][c] for r in range(self.rows)]
            for c in range(self.cols)
        ]


def scroll_text_on_multiple_matrices(controllers, text, delay=0.1, skip_end_space=False, threaded=False):
    if threaded:
        from threading import Thread
        threads = []

        for controller in controllers:
            threads.append(Thread(target=controller.scroll_text, args=(text, delay, skip_end_space)))

        for thread in threads:
            thread.start()

        return threads
    else:
        for controller in controllers:
            controller.scroll_text(text, delay, skip_end_space)

    return None

