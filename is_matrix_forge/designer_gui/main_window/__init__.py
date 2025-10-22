import json
from typing import List, Tuple, Any, Dict
import PySimpleGUI as sg
import copy
import os
import json

from is_matrix_forge.led_matrix.helpers.device import DEVICES
from is_matrix_forge.led_matrix.display.animations.frame.base import Frame
from is_matrix_forge.led_matrix.display.grid.helpers import is_valid_grid
from is_matrix_forge.led_matrix.display.animations.frame.helpers import is_valid_frames
from is_matrix_forge.designer_gui.main_window.layout import PixelGridLayout
from is_matrix_forge.led_matrix.display.helpers import render_matrix


sg.theme('DarkTeal2')


def _normalize(key: Any) -> str:
    s = str(key)
    for ch in " <>,'()":
        s = s.replace(ch, '_')
    return s.strip('_')


class PixelGrid:
    """
    LED matrix pixel grid UI with frame-by-frame animation.
    """
    def __init__(self, width: int = 9, height: int = 34):
        self.__width = None
        self.__height = None
        self.__frames = None
        self.__current_frame = None
        self.__grid = None
        self.__preferred_device = None

        self.width = width
        self.height = height

        base = [[0] * self.height for _ in range(self.width)]
        self.frames = [Frame(copy.deepcopy(base), width=self.width, height=self.height)]
        self.current_frame = 0
        self.grid = self.frames[0].get_grid_data()
        self.preferred_device = None

        layout = PixelGridLayout(self.width, self.height).build()
        self.window = sg.Window('Pixel Grid', layout, finalize=True, resizable=True)
        self._init_button_colors()
        self._update_frame_indicator()

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
    def frames(self) -> List[Frame]:
        return self.__frames

    @frames.setter
    def frames(self, value: Any) -> None:
        if not isinstance(value, list) or len(value) == 0 or not all(isinstance(f, Frame) for f in value):
            raise TypeError("frames must be a non-empty list of Frame objects")
        self.__frames = value

    @property
    def current_frame(self) -> int:
        return self.__current_frame

    @current_frame.setter
    def current_frame(self, value: Any) -> None:
        """
        Setter indicating which frame index to display..

        Note:
            Must be an integer between 0 and len(frames) - 1.
        """
        if not isinstance(value, int) or not (0 <= value < len(self.frames)):
            raise ValueError("current_frame must be an index into frames list")
        self.__current_frame = value

    @property
    def grid(self) -> List[List[int]]:
        """
        A column-major 0/1 list representing the pixel grid.
        """
        return self.__grid

    @grid.setter
    def grid(self, value: Any) -> None:
        """
        Setter for the grid data.

        Note:
            A valid grid is structured as follows:
              - Must be a list
                - Containing 9 lists
                  - Each list:
                    - Must be the same length
                    - Each item:
                      - Integer
                      - 0-1

            Example:
                Framework Laptop 9x34:
                    - 9 lists
                      - each with 34 items
                        - 0-1
        """
        if not is_valid_grid(value, self.width, self.height):
            raise ValueError("Grid must match width/height and be 0/1 values")
        self.__grid = value
        # update frame's grid as well
        if hasattr(self, 'frames') and self.frames:
            self.frames[self.current_frame].grid = value

    @property
    def preferred_device(self):
        """
        The device we want to send the grid to.
        """
        return self.__preferred_device

    @preferred_device.setter
    def preferred_device(self, value: Any) -> None:
        # no strict type check, but could enforce presence in DEVICES
        self.__preferred_device = value

    def _init_button_colors(self) -> None:
        for col in range(self.width):
            for row in range(self.height):
                state = self.grid[col][row]
                color = 'green' if state else 'lightgrey'
                self.window[(col, row)].update(button_color=('black', color))

    def _update_frame_indicator(self) -> None:
        total = len(self.frames)
        idx = self.current_frame + 1
        dur = self.frames[self.current_frame].duration
        self.window['FRAME_INDICATOR'].update(
            f'Frame {idx}/{total} (Duration: {dur}s)'
        )

    def run(self) -> None:
        """
        Run the UI.
        """
        while True:
            event, _ = self.window.read()
            if event in (sg.WINDOW_CLOSED, 'Exit'):
                break
            handler = getattr(self, f'_handle_{_normalize(event)}', None)
            if callable(handler):
                handler(event)
            elif isinstance(event, tuple):
                self._toggle_pixel(event)
        self.window.close()

    def _toggle_pixel(self, key: Tuple[int, int]) -> None:
        col, row = key
        new = 1 - self.grid[col][row]
        print(f'Pixel {col},{row} toggled from {self.grid[col][row]} to {new}')
        self.grid = [[new if (c==col and r==row) else self.grid[c][r]
                      for r in range(self.height)]
                     for c in range(self.width)]
        self.window[key].update(
            button_color=('black', 'green' if new else 'lightgrey')
        )

    # Frame management
    def add_frame(self) -> None:
        """
        Add a new frame to the grid.
        """
        new_grid = copy.deepcopy(self.grid)
        frm = Frame(new_grid, width=self.width, height=self.height)
        self.frames = self.frames + [frm]
        self.current_frame = len(self.frames) - 1
        self.grid = frm.get_grid_data()
        self._init_button_colors()
        self._update_frame_indicator()

    def prev_frame(self) -> None:
        """
        Go back one frame.

        Show the frame that's before the current one.
        """
        if self.current_frame > 0:
            self.current_frame -= 1
            self._load_frame()

    def next_frame(self) -> None:
        if self.current_frame < len(self.frames) - 1:
            self.current_frame += 1
            self._load_frame()

    def _load_frame(self) -> None:
        frm = self.frames[self.current_frame]
        self.grid = frm.get_grid_data()
        self._init_button_colors()
        self._update_frame_indicator()

    # Export handlers
    def _handle_Export(self, _event) -> None:
        data = [f.get_grid_data() for f in self.frames] if len(self.frames) > 1 else self.frames[0].get_grid_data()
        print(data)

    def _handle_Export_to_File(self, _event) -> None:
        path = sg.popup_get_file(
            'Save Grid As', save_as=True, no_window=True,
            file_types=(('JSON Files', '*.json'),), default_extension='.json'
        )
        if not path:
            return
        data = [f.get_grid_data() for f in self.frames] if len(self.frames) > 1 else self.frames[0].get_grid_data()
        try:
            with open(path, 'w') as f:
                json.dump(data, f)
            sg.popup('Success', f'Saved to {os.path.basename(path)}')
        except Exception as e:
            sg.popup_error('Error', str(e))

    def _handle_Load_from_File(self, _event) -> None:
        path = sg.popup_get_file(
            'Load Grid From', no_window=True,
            file_types=(('JSON Files', '*.json'),)
        )
        if not path:
            return
        try:
            raw = json.load(open(path))
            if is_valid_grid(raw, self.width, self.height):
                grids = [raw]
            elif is_valid_frames(raw, self.width, self.height):
                grids = raw
            else:
                sg.popup_error('Invalid format')
                return
            self.frames = [Frame(copy.deepcopy(g), width=self.width, height=self.height) for g in grids]
            self.current_frame = 0
            self._load_frame()
            sg.popup('Success', f'Loaded {len(self.frames)} frame(s)')
        except Exception as e:
            sg.popup_error('Error', str(e))

    # Send to matrix
    def _handle_Send_to_Matrix(self, _event) -> None:
        devices = DEVICES
        if not devices:
            sg.popup_error('No devices found.')
            return
        if self.preferred_device in devices:
            dev = self.preferred_device
        else:
            descs = [f"{d.device} - {d.description}" for d in devices]
            win = sg.Window('Select Device', [
                [sg.Text('Select device:')],
                [sg.Listbox(descs, size=(40, len(descs)), key='DEV')],
                [sg.Checkbox('Always choose', key='REM')],
                [sg.OK(), sg.Cancel()]
            ], modal=True)
            ev, vals = win.read(); win.close()
            if ev != 'OK' or not vals['DEV']:
                return
            dev = devices[descs.index(vals['DEV'][0])]
            if vals['REM']:
                self.preferred_device = dev
        try:
            render_matrix(dev, self.grid)
            sg.popup('Success', f'Sent to {dev.device}')
        except Exception as e:
            sg.popup_error('Error sending:', str(e))

    # Button-mapped handlers
    def _handle_Add_Frame(self, e): self.add_frame()
    def _handle_Prev(self, e): self.prev_frame()
    def _handle_Next(self, e): self.next_frame()

    def _validate(self, grid: Any) -> bool:
        return is_valid_grid(grid, self.width, self.height)


def main():
    PixelGrid().run()


if __name__ == '__main__':
    main()
