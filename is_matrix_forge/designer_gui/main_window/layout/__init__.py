import PySimpleGUI as sg
from typing import List, Tuple, Any
from is_matrix_forge.designer_gui.main_window.layout.button_grid.column import build_grid_frame


class PixelGridLayout:
    """
    Builds the PySimpleGUI layout for the pixel grid, control panel,
    and frame animation controls.
    """
    def __init__(
        self,
        width: int = 9,
        height: int = 34,
        button_list: List[str] = None,
        pad: Tuple[int, int] = (0, 0),
        button_size: Tuple[int, int] = (2, 1)
    ):
        # initialize backing fields
        self.__width = None
        self.__height = None
        self.__pad = None
        self.__button_size = None
        self.__button_list = None
        # assign via properties
        self.width = width
        self.height = height
        self.pad = pad
        self.button_size = button_size
        self.button_list = button_list or [
            'Export', 'Export to File', 'Load from File',
            'Send to Matrix', 'Add Frame', 'Exit'
        ]

    @property
    def width(self) -> int:
        return self.__width

    @width.setter
    def width(self, value: Any) -> None:
        if not isinstance(value, int) or value <= 0:
            raise TypeError("Width must be a positive integer")
        self.__width = value

    @property
    def height(self) -> int:
        return self.__height

    @height.setter
    def height(self, value: Any) -> None:
        if not isinstance(value, int) or value <= 0:
            raise TypeError("Height must be a positive integer")
        self.__height = value

    @property
    def pad(self) -> Tuple[int, int]:
        return self.__pad

    @pad.setter
    def pad(self, value: Any) -> None:
        if (
            not isinstance(value, tuple)
            or len(value) != 2
            or not all(isinstance(v, int) for v in value)
        ):
            raise TypeError("pad must be a tuple of two integers")
        self.__pad = value

    @property
    def button_size(self) -> Tuple[int, int]:
        return self.__button_size

    @button_size.setter
    def button_size(self, value: Any) -> None:
        if (
            not isinstance(value, tuple)
            or len(value) != 2
            or not all(isinstance(v, int) for v in value)
        ):
            raise TypeError("button_size must be a tuple of two integers")
        self.__button_size = value

    @property
    def button_list(self) -> List[str]:
        return self.__button_list

    @button_list.setter
    def button_list(self, value: Any) -> None:
        if (
            not isinstance(value, list)
            or not all(isinstance(v, str) for v in value)
        ):
            raise TypeError("button_list must be a list of strings")
        self.__button_list = value

    def build(self) -> List[List[Any]]:
        grid_column = build_grid_frame(self.width, self.height, button_size=self.button_size, pad=self.pad)

        controls = [[sg.Button(btn)] for btn in self.button_list]
        control_column = sg.Column(controls, vertical_alignment='top')

        frame_controls = [
            sg.Button('< Prev', key='<Prev>'),
            sg.Text('', key='FRAME_INDICATOR'),
            sg.Button('Next >', key='Next>')
        ]

        layout = [
            [grid_column, sg.VerticalSeparator(), control_column],
            [sg.HorizontalSeparator(pad=(0, 5))],
            [sg.Push(), *frame_controls, sg.Push()]
        ]
        return layout