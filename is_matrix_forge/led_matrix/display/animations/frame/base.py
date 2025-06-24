# is_matrix_forge.led_matrix.display.animations.frame.base
# Standard library imports

from time import sleep

from typing import List, Any, Union
from is_matrix_forge.led_matrix.display.grid.helpers import is_valid_grid

from is_matrix_forge.led_matrix.display.helpers import render_matrix
from is_matrix_forge.led_matrix.display.grid.grid import Grid
from is_matrix_forge.led_matrix.display.grid.helpers import generate_blank_grid


class Frame:
    """
    Represents a single animation frame with a duration.
    """
    DEFAULT_DURATION = 0.33

    def __init__(self, grid: Union[List[List[int]], Grid], duration: float = 1.0):
        self.__grid = None
        self.__number_of_plays = 0
        self.__duration = duration

        # Accept Grid instances by extracting their underlying data
        if grid is None:
            grid = generate_blank_grid()
        elif isinstance(grid, Grid):
            # Grid stores column-major lists in _grid
            grid = getattr(grid, '_grid', list(grid))

        # Determine dimensions from column-major layout
        self.__width = len(grid)
        self.__height = len(grid[0])
        # Validate and store grid data
        self.grid = grid

        if duration is not None:
            self.duration = duration

    @property
    def duration(self) -> float:
        """
        The time the program should wait after displaying this frame before moving to the next.

        Returns:
            float: Frame duration in seconds.
        """
        return self.__duration or self.DEFAULT_DURATION

    @duration.setter
    def duration(self, new: Union[float, int, str]):
        """
        Set the duration of the frame in seconds.

        Parameters:
            new (Union[float, int, str]):
                The duration of the frame in seconds, or fraction thereof, or a string.
        """
        try:
            dur = float(new)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid duration: {new}") from e
        if dur < 0:
            raise ValueError(f"Duration must be positive, not {dur}")
        self.__duration = dur

    @property
    def grid(self) -> List[List[int]]:
        return self.__grid

    @grid.setter
    def grid(self, value: Any) -> None:
        # If user passed a Grid, unwrap to list-of-columns
        #if isinstance(value, Grid):
        #    value = getattr(value, '_grid', list(value))
        # if not is_valid_grid(value, self.__width, self.__height):
        #    raise ValueError(f"Grid must be {self.__width}x{self.__height} list of 0/1")
        self.__grid = value

    @property
    def number_of_plays(self) -> int:
        return self.__number_of_plays

    @number_of_plays.setter
    def number_of_plays(self, new: int) -> None:
        if not isinstance(new, int) or new < 0:
            raise ValueError("Number of plays must be a non-negative integer")
        self.__number_of_plays = new

    def __repr__(self) -> str:
        return f"Frame(grid={self.grid}, duration={self.duration})"

    @staticmethod
    def from_dict(data: dict) -> 'Frame':
        """
        Create a `Frame` object directly from a properly formatted dictionary.

        Parameters:
            data (dict): A dictionary containing 'grid' and optional 'duration'.
        Returns:
            Frame: A new `Frame` object.
        """
        try:
            return Frame(
                grid=data['grid'],
                duration=data.get('duration', Frame.DEFAULT_DURATION)
            )
        except KeyError as e:
            raise e from e

    def play(self, device) -> None:
        """
        Play the frame on the LED matrix device.
        """
        device.draw_grid(self.grid)
        sleep(self.duration)
        self.__number_of_plays += 1



# class Frame:
#     """
#     Represents a single animation frame with a duration.
#     """
#     DEFAULT_DURATION = 0.33
#
#     def __init__(self, grid: List[List[int]], duration: float = 1.0):
#         self.__grid = None
#         self.__number_of_plays = 0
#         self.__duration = duration
#
#         if grid is None:
#             grid = generate_blank_grid()
#
#         self.__width  = len(grid)
#         self.__height = len(grid[0])
#         self.grid = grid
#
#         if duration is not None:
#             self.duration = duration
#
#     @property
#     def duration(self) -> float:
#         """
#         The time the program should wait after displaying this frame before moving to the next.
#
#         Parameters:
#
#         """
#
#         return self.__duration or self.DEFAULT_DURATION
#
#     @duration.setter
#     def duration(self, new: Union[float, int, str]):
#         """
#         Set the duration of the frame in seconds.
#
#         Parameters:
#             new (Union[float, int, str]):
#                 The duration of the frame in seconds, or fractions thereof, or a string representing a fraction of a
#                 second/full-second.
#         """
#         try:
#             dur = float(new)
#         except (TypeError, ValueError) as e:
#             raise ValueError(f"Invalid duration: {new}") from e
#         if dur < 0:
#             raise ValueError(f"Duration must be positive, not {dur}")
#         self.__duration = dur
#
#     @property
#     def grid(self) -> List[List[int]]:
#         return self.__grid
#
#     @grid.setter
#     def grid(self, value: Any) -> None:
#         if not is_valid_grid(value, self.__width, self.__height):
#             raise ValueError(f"Grid must be {self.__width}x{self.__height} list of 0/1")
#         self.__grid = value
#
#     @property
#     def number_of_plays(self):
#         return self.__number_of_plays
#
#     @number_of_plays.setter
#     def number_of_plays(self, new: int) -> None:
#         if not isinstance(new, int) or new < 0:
#             raise ValueError("Number of plays must be a non-negative integer")
#         self.__number_of_plays = new
#
#     def __repr__(self) -> str:
#         return f"Frame(grid={self.grid}, duration={self.duration})"
#
#     # width/height context for validation inherited from usage
#     @property
#     def width(self) -> int:
#         return self.__width
#
#     @property
#     def height(self) -> int:
#         return self.__height
#
#     @staticmethod
#     def from_dict(data: dict) -> 'Frame':
#         """
#         Create a `Frame` object directly from a properly formatted dictionary.
#
#         The dictionary must contain the following keys:
#             - `grid`:
#                 A list of lists representing the grid of the frame.
#
#             - `duration`:
#                 The duration of the frame in seconds.
#
#         Parameters:
#             data (dict):
#                 A dictionary containing the data for the frame.
#
#         Returns:
#             Frame:
#                 A new `Frame` object.
#         """
#         try:
#             return Frame(
#                 grid=data['grid'],
#                 duration=data['duration']
#             )
#         except KeyError as e:
#             key = e.args[0]
#             if key == 'duration':
#                 return Frame(
#                     grid=data['grid'],
#                     duration=Frame.DEFAULT_DURATION
#                 )
#             else:
#                 raise e from e
#
#     def play(self, device) -> None:
#         """
#         Play the frame on the LED matrix.
#         """
#         render_matrix(device, self.grid)
#         sleep(self.duration)
#         self.__number_of_plays += 1
