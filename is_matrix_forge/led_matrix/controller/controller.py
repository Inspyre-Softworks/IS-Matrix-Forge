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
from __future__ import annotations

import threading
from time import sleep
from typing import Optional, Dict, Any, Union, List

from inspyre_toolbox.syntactic_sweets.classes import validate_type
from inspyre_toolbox.syntactic_sweets.classes.decorators.aliases import add_aliases, method_alias
from serial.tools.list_ports_common import ListPortInfo

from is_matrix_forge.common.helpers import coerce_to_int
from is_matrix_forge.led_matrix.constants import SLOT_MAP
from is_matrix_forge.led_matrix.display.text import show_string as _show_string_raw
from is_matrix_forge.led_matrix.controller import MultitonMeta
from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized
from is_matrix_forge.led_matrix.commands.map import CommandVals
from is_matrix_forge.led_matrix.hardware import send_serial, send_command
from is_matrix_forge.led_matrix.display.effects.breather import Breather
from is_matrix_forge.led_matrix.display.text import show_string

COMMANDS = CommandVals


@add_aliases
class LEDMatrixController(metaclass=MultitonMeta):
    """
    Controller class for LED Matrix devices.

    This class provides a high-level interface for interacting with LED matrix
    hardware devices. It handles device communication, animation control,
    pattern display, and other operations.

    Properties:
        device (ListPortInfo):
            The connected LED matrix device.

        animating (bool):
            Whether the device is currently animating.

        location (dict):
            Physical location information for the device.

        location_abbrev (str):
            Abbreviated location identifier.

        side_of_keyboard (str):
            Which side of the keyboard the device is on.

        slot (int):
            The slot number of the device.
    """
    FACTORY_DEFAULT_BRIGHTNESS = 75
    """ 
    Default brightness level as a percentage of maximum 
    brightness (0-100).
    """

    COMMANDS                   = COMMANDS
    """ Command map for the LED matrix hardware."""

    def __init__(
            self,
            device,
            default_brightness:           Optional[int]  = None,
            skip_init_brightness_set:     Optional[bool] = False,
            skip_init_clear:              Optional[bool] = False,
            init_grid:                    Optional[Grid] = None,
            do_not_show_grid_on_init:     Optional[bool] = False,
            thread_safe:                  Optional[bool] = False,
            do_not_warn_on_thread_misuse: Optional[bool] = False,
            hold_all:                     Optional[bool] = False
    ):
        """
        Initialize a new LED Matrix Controller.

        Parameters:
            device (ListPortInfo):
                The LED matrix device to control.

            default_brightness (Union[int, float, str]):
                Default brightness level (0-100).
        """
        self.__current_animation      = None
        if default_brightness is None:
            default_brightness = self.FACTORY_DEFAULT_BRIGHTNESS
        self.__default_brightness = self.__normalize_percent(default_brightness)
        self.__breather               = None
        self.__brightness             = None
        self.__built_in_patterns      = None
        self.__device                 = None
        self.__grid                   = None
        self.__hold_all               = None
        self.__init_clear             = None
        self.__keep_image             = False
        self.__name                   = None
        self.__image_retention_worker = None
        self.__set_brightness_on_init = None
        self.__show_grid_on_init      = None
        self._thread_safe             = None
        self._cmd_lock                = None
        self._keep_alive              = False
        self._KEEP_ALIVE_INTERVAL    = 50

        self.hold_all = hold_all or False

        if skip_init_brightness_set is not None:
            if not isinstance(skip_init_brightness_set, bool):
                raise TypeError('skip_init_brightness_set must be a boolean.')
            self.__set_brightness_on_init = not skip_init_brightness_set

        if skip_init_clear is not None:
            if not isinstance(skip_init_clear, bool):
                raise TypeError('skip_init_clear must be a boolean.')
            self.__init_clear = not skip_init_clear

        if init_grid is not None:
            from is_matrix_forge.led_matrix.display.grid import Grid
            if not isinstance(init_grid, Grid):
                raise TypeError(f'init_grid must be of type `Grid`, not {type(init_grid)}')

            self.__grid = init_grid

        if do_not_show_grid_on_init is not None:
            if not isinstance(do_not_show_grid_on_init, bool):
                raise TypeError('do_not_show_grid_on_init must be a boolean.')
            self.__show_grid_on_init = not do_not_show_grid_on_init

        self.device = device

        self.__set_up_thread_safety__(thread_safe)

        self.__post_init__()

        # ---------------------------------------------------------------------
        # Keep‑alive internal worker
        # ---------------------------------------------------------------------

    def __keep_alive_worker(self):
        """Loop until signalled, polling :pyattr:`animating` every 50 s."""
        # Lazily create the stop event (should already exist, but be safe)
        stop_evt = self._keep_alive_stop_evt or threading.Event()
        self._keep_alive_stop_evt = stop_evt

        while not stop_evt.is_set():
            try:
                _ = self.animating  # A simple query is enough to keep FW awake
            except Exception:  # pragma: no cover – we don't crash the thread
                pass

            # Wait with timeout so the thread can exit early when stop_evt is set
            stop_evt.wait(self._KEEP_ALIVE_INTERVAL)

        # ---------------------------------------------------------------------
        # Property controlling the keep‑alive thread
        # ---------------------------------------------------------------------

    @property
    def keep_alive(self) -> bool:
        """Whether the background keep‑alive thread is active."""
        return self._keep_alive

    @keep_alive.setter
    def keep_alive(self, enable: bool):
        if not isinstance(enable, bool):
            raise TypeError('keep_alive must be a boolean.')

        # No change ➜ nothing to do
        if enable == self._keep_alive:
            return

        if enable:
            # Start background thread
            self._keep_alive_stop_evt = threading.Event()
            self._keep_alive_thread = threading.Thread(
                target=self.__keep_alive_worker,
                name=f"{self.__class__.__name__}-KeepAlive-{self.device.name}",
                daemon=True,
            )
            self._keep_alive_thread.start()
            self._keep_alive = True
        else:
            # Signal thread to exit and wait (briefly) for it
            if self._keep_alive_stop_evt is not None:
                self._keep_alive_stop_evt.set()
            if (
                    self._keep_alive_thread is not None
                    and self._keep_alive_thread.is_alive()
            ):
                self._keep_alive_thread.join(timeout=self._KEEP_ALIVE_INTERVAL + 1)
            self._keep_alive_thread = None
            self._keep_alive_stop_evt = None
            self._keep_alive = False
        self.__post_init__()

    def __post_init__(self):
        from is_matrix_forge.led_matrix.display.effects.breather import Breather

        self.__breather = Breather(self)

        if self.clear_on_init:
            self.clear()

        if self.set_brightness_on_init:
            self.set_brightness(self.__default_brightness)

        if self.grid and self.show_grid_on_init:
            self.draw_grid()

        if not self.__built_in_patterns:
            from is_matrix_forge.led_matrix.display.patterns.built_in import BuiltInPatterns
            self.__built_in_patterns = BuiltInPatterns(self)

        if self.breather is None:
            self.__breather = Breather(self)

    def __set_up_thread_safety__(self, thread_safe_opt: bool):
        if thread_safe_opt is None or not thread_safe_opt:
            self._thread_safe = False
            return
        else:
            self._thread_safe = True

            return

    @property
    def animating(self) -> bool:
        """
        Check if the device is currently animating.

        Returns:
            bool: True if the device is animating, False otherwise.
        """
        return bool(send_command(self.device, COMMANDS.Animate, with_response=True)[0])
        # return animate(self.device)

    @property
    def breather(self) -> Breather:
        """
        Get the Breather instance associated with the LED matrix controller.

        .. note::
            This is a read-only property.
        """
        return self.__breather

    @property
    def breathing(self) -> bool:
        return self.breather.breathing

    @breathing.setter
    def breathing(self, new: bool):
        self.breather.breathing = new

    @property
    def brightness(self):
        """
        Get the current brightness level of the LED matrix.

        Returns:
            int or float: The current brightness value, or the default if not set.
        """
        return self.__brightness or self.__default_brightness

    @brightness.setter
    def brightness(self, new):
        self.set_brightness(new, True)
        self.__brightness = new

    @property
    def built_in_pattern_names(self) -> List:
        return self.get_built_in_pattern_names()

    @property
    def clear_on_init(self):
        return self.__init_clear

    @property
    def cmd_lock(self):
        if self._cmd_lock is None and self.thread_safe is True:
            self._cmd_lock = threading.RLock()

        return self._cmd_lock

    @property
    def current_animation(self):
        return self.__current_animation

    @property
    def device(self) -> ListPortInfo:
        """
        Get the current LED matrix device.

        Returns:
            ListPortInfo: The current device.
        """
        return self.__device

    @validate_type(ListPortInfo)
    @device.setter
    def device(self, device: ListPortInfo):
        """
        Set the LED matrix device.

        Parameters:
            device (ListPortInfo):
                The device to control.

        Raises:
            ValueError:
                If `device` is `None` or empty.
        """
        if not device:
            raise ValueError('Device cannot be None or empty.')

        self.__device = device


    @property
    def grid(self):
        """
        The grid currently displayed on the device.

        Returns:
            Grid:
                The grid currently displayed on the device.
        """
        return self.__grid

    @property
    def keep_image(self):
        """
        Whether the controller has been instructed to keep the current grid showing.

        Returns:
            bool:
                - True; if the controller has been instructed to keep the current grid showing.
                - False; if the controller has not been instructed to keep the current grid showing.

        """
        return self.__keep_image

    @validate_type(bool)
    @keep_image.setter
    def keep_image(self, new):
        self.__keep_image = new

    @property
    def location(self) -> Dict[str, Any]:
        """
        Get the physical location information for the device.

        Returns:
            Dict[str, Any]:
                A dictionary containing location information such as abbreviation, side, and slot.
        """
        return SLOT_MAP.get(self.device.location)

    @property
    def location_abbrev(self) -> str:
        """
        Get the abbreviated location identifier for the device.

        Returns:
            str:
                The abbreviated location identifier (e.g., 'R1', 'L2').
        """
        return self.location['abbrev']

    @property
    def name(self) -> str:
        return self.__name if self.__name is not None else self.device.name

    def play_animation(self, animation):
        from is_matrix_forge.led_matrix.display.animations.animation import Animation

        if not isinstance(animation, Animation):
            raise TypeError(f'Expected `Animation`; got `{type(animation)}`!')

        self.__current_animation = animation

        return animation.play(devices=[self])

    def scroll_text(self, text: str, skip_end_space: bool = False, loop: bool = False):
        from is_matrix_forge.led_matrix.display.text.scroller import TextScroller
        from is_matrix_forge.led_matrix.display.animations.animation import Animation
        from is_matrix_forge.led_matrix import fonts as font

        text_animation = Animation(TextScroller(font).scroll(text, skip_end_space))
        text_animation.set_all_frame_durations(.03)
        if loop:
            text_animation.loop = True
        return self.play_animation(text_animation)

    def show_text(self, text: str):
        self.draw_text(text)

    @property
    def set_brightness_on_init(self):
        """
        Whether the controller was instructed to set the brightness on init.

        Returns:
            bool:
                - True; if the controller was instructed to set the brightness on init.
                - False; if the controller was instructed to forego setting the brightness on init.
        """
        return self.__set_brightness_on_init

    @property
    def show_grid_on_init(self) -> bool:
        return self.__show_grid_on_init

    @property
    def side_of_keyboard(self) -> str:
        """
        Get which side of the keyboard the device is on.

        Returns:
            str:
                The side of the keyboard ('left' or 'right').
        """
        return self.location['side']

    @property
    def slot(self) -> int:
        """
        Get the slot number of the device.

        Returns:
            int:
                The slot number (1 or 2).
        """
        return self.location['slot']

    @property
    def thread_safe(self):
        return self._thread_safe

    @synchronized
    def animate(self, enable: bool = True) -> None:
        """
        Control animation on the LED matrix.

        Parameters:
            enable (bool, optional):
                Whether to enable or disable animation. Defaults to True.
        """
        from is_matrix_forge.led_matrix.hardware import animate

        # Call the low-level animate function to control animation on the device
        # The animate function also sets the status to 'animate' when enabled
        animate(self.device, enable)

    @synchronized
    def clear_matrix(self) -> None:
        """
        Clear the LED matrix display.

        Generates a blank grid and displays it on the LED matrix.
        """
        from is_matrix_forge.led_matrix.display.grid.helpers import generate_blank_grid
        from is_matrix_forge.led_matrix.display.grid import Grid

        data = generate_blank_grid()
        self.__keep_image = False
        grid = Grid(init_grid=data)
        self.draw_grid(grid)

    def clear(self):
        self.clear_matrix()

    def draw(self, grid: 'Grid' = None) -> None:
        return self.draw_grid(grid)

    @synchronized
    def draw_grid(self, grid: 'Grid' = None) -> None:
        """
        Draw a grid on the LED matrix.

        Parameters:
            grid (Grid):
                The grid to display on the LED matrix.
        """
        from is_matrix_forge.led_matrix.display.grid import Grid
        from is_matrix_forge.led_matrix.display.helpers import render_matrix

        grid = grid or self.grid
        if not isinstance(grid, Grid):
            grid = Grid(init_grid=grid)
        render_matrix(self.device, grid.grid)

    @synchronized
    @method_alias('pattern')
    def draw_pattern(self, pattern: str) -> None:
        """
        Draw a pattern on the LED matrix.

        Parameters:
            pattern (str):
                The pattern string to display.

        Note:
            This method is aliased as 'pattern'.
        """
        from is_matrix_forge.led_matrix.display.patterns.built_in import BuiltInPatterns
        pattern_pen = BuiltInPatterns(self)
        pattern_pen.render(pattern)

    @synchronized
    def draw_percentage(self, percentage: int, clear_first: bool = False):
        from is_matrix_forge.led_matrix.hardware import percentage as _show_percentage_raw
        if not isinstance(percentage, int):
            if isinstance(percentage, (float, str)):
                percentage = coerce_to_int(percentage)
            else:
                raise TypeError(f'Percentage must be of type `int`. Not {type(percentage)}!')

        if not 0 <= percentage <= 100:
            raise ValueError('Percentage must be between 0 and 100')

        if clear_first:
            self.clear()

        _show_percentage_raw(self.device, percentage)

    def draw_string(self, text: str):
        self.show_text(text)

    def draw_text(self, text: str):
        self.show_text(text)

    @synchronized
    def display_location(self):
        """
        Show the location abbreviation on the LED matrix.

        Returns:
            None
        """
        from is_matrix_forge.led_matrix.display.text import show_string as _show_string_raw
        _show_string_raw(self.device, self.location_abbrev)

    @synchronized
    def display_name(self):
        """
        Shoe the device name (com port, unless named explicitly) on the LED matrix.

        Returns:
            None
        """
        _show_string_raw(self.device, self.name)

    def get_built_in_pattern_names(self) -> List:
        from is_matrix_forge.led_matrix.display.patterns.built_in.stencils.res import PATTERN_MAP

        return list(PATTERN_MAP.keys())


    @synchronized
    def halt_animation(self) -> None:
        """
        Stop any ongoing animation on the LED matrix.

        This method checks if animation is currently running and stops it if needed.
        """
        # Check if animation is currently running
        if self.animating:
            # Call animate with False to stop the animation
            self.animate(False)

    @synchronized
    def identify(
            self,
            skip_clear: bool  = False,
            duration:   float = 20.0,
            cycles:     int   = 3
    ) -> None:
        """
        Display identification information on the LED matrix.

        Shows the location abbreviation and device name for the specified number
        of cycles, distributing the total duration evenly across all messages.

        Parameters:
            skip_clear (bool, optional):
                If True, doesn't clear the display after identification (optional, defaults to `False`).

            duration (float, optional):
                The duration of the identification animation in seconds (optional, defaults to 20.0).

            cycles (int, optional):
                The number of times to repeat each identification message/animation (optional, defaults to 3).
        """
        if not skip_clear:
            self.clear()

        messages = (self.location_abbrev, self.device.name)
        if duration is not None and not isinstance(duration, (float, int)):
            if isinstance(duration, str):
                duration = float(duration)
            else:
                raise TypeError("Duration must be a float or integer.")
        interval = duration / (cycles * len(messages))

        for _ in range(cycles):
            for msg in messages:
                _show_string_raw(self.device, msg)
                sleep(interval)

        if not skip_clear:
            self.clear()

    @property
    def is_animating(self):
        return self.animating

    def jump_to_bootloader(self):
        """
        Jump to the bootloader on the device.

        Returns:
            None
        """
        from is_matrix_forge.led_matrix.hardware import bootloader_jump
        bootloader_jump(self.device)

    def list_patterns(self):
        print

    @synchronized
    def set_brightness(self, brightness: Union[int, float], __from_setter=False) -> None:
        """
        Set the brightness level of the LED matrix.

        Parameters:
            brightness (Union[int, float]):
                Brightness level as a percentage (0-100).

        Raises:
            InvalidBrightnessError:
                If the brightness value is invalid.
        """
        from is_matrix_forge.led_matrix.hardware import brightness as _set_brightness_raw
        from is_matrix_forge.led_matrix.errors import InvalidBrightnessError
        from is_matrix_forge.common.helpers import \
            percentage_to_value  # Converts percentage values to raw hardware values

        # Convert the percentage (0-100) to a hardware-specific value
        # The hardware expects a different range than the user-friendly percentage
        brightness_value = percentage_to_value(max_value=255, percent=brightness)

        try:
            # Call the low-level function to set the brightness on the device
            _set_brightness_raw(self.device, brightness_value)
        except ValueError as e:
            # If the low-level function raises a ValueError, wrap it in our custom
            # InvalidBrightnessError to provide more context about the error
            raise InvalidBrightnessError(brightness_value) from e

        if not __from_setter:
            self.__brightness = brightness

    def show_string(self, text: str) -> None:
        """
        Alias for LEDMatrixController.show_text.

        See Also:
            LEDMatrixController.show_text
        """
        self.show_text(text)

    @synchronized
    def show_text(self, text: str) -> None:
        """
        Show text on the LED matrix.
        """
        show_string(self.device, text)

    @staticmethod
    # Internal methods
    def __normalize_percent(val: Union[int, float, str]) -> int:
        """
        Normalize a percentage value to an integer between 0 and 100.

        Parameters:
            val (Union[int, float, str]):
                The value to normalize.
                This value can be an integer, float, or string (with or without '%').

        Returns:
            int:
                Normalized percentage value as an integer between 0 and 100.

        Raises:
            ValueError:
                If the percentage is not between 0 and 100.
        """
        # Handle string input (e.g., "75%") by stripping the '%' character and converting to float
        if isinstance(val, str):
            val = float(val.strip("%"))

        # Convert to float first to handle any decimal values, then round and convert to int
        # This ensures consistent handling of values like 75.6 (becomes 76)
        percent = int(round(float(val)))

        # Validate that the percentage is within the valid range (0-100)
        if not (0 <= percent <= 100):
            raise ValueError("Percentage must be between 0 and 100")

        return percent

    def __repr__(self) -> str:
        """
        Return a string representation of the LEDMatrixController.

        Returns:
            str:
                A string representation including the device, location, and brightness.
        """
        dev = self.__dict__.get('_LEDMatrixController__device', None)

        if hasattr(dev, 'device'):
            dev_key = dev.device
        elif hasattr(dev, 'name'):
            dev_key = dev.name
        else:
            dev_key = repr(dev)

        loc_key = (self.location or {}).get('abbrev', repr(self.location))

        return (f"<{self.__class__.__name__} "
                f"device={dev_key!r} "
                f"location={loc_key!r} "
                f"brightness={self.__default_brightness}%>")

    def __setattr__(self, name, *args, **kwargs):
        if name == 'FACTORY_DEFAULT_BRIGHTNESS':
            raise AttributeError("FACTORY_DEFAULT_BRIGHTNESS is a read-only attribute")

        super().__setattr__(name, *args, **kwargs)
