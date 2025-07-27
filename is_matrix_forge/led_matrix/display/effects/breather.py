import threading
import time
import contextlib
from is_matrix_forge.common.decorators.freeze_setter import freeze_setter
from is_matrix_forge.log_engine import ROOT_LOGGER, Loggable


MOD_LOGGER = ROOT_LOGGER.get_child(__name__)


class Breather(Loggable):
    """
    Controls a “breathing” (fade in/out) effect on a controller’s brightness.

    Parameters:
        controller:
            Any object with a mutable `brightness` attribute (0–100).

        min_brightness (int):
            Lowest brightness in the cycle. Defaults to 5.

        max_brightness (int):
            Highest brightness in the cycle. Defaults to 90.

        step (int):
            Amount to change brightness each tick. Defaults to 5.

        breathe_fps (float):
            How many brightness updates per second. Defaults to 30.

    Methods:

        start():
            Launch the breathing loop in a background thread.

        stop():
            Halt the breathing loop and join the thread.
    """
    def __init__(
            self,
            controller,
            min_brightness: int   = 5,
            max_brightness: int   = 90,
            step:           int   = 5,
            breathe_fps:    float = 30.0
    ):
        super().__init__(MOD_LOGGER)
        self._controller     = None
        self._min_brightness = None
        self._max_brightness = None
        self._step           = None
        self._fps            = None
        self._pause_event = threading.Event()

        self.controller = controller
        log = self.class_logger
        self.__initial_brightness = self.controller.brightness
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.step = step
        self.fps = breathe_fps
        log.debug(
            "Breather initialized (min=%s max=%s step=%s fps=%s)",
            self.min_brightness,
            self.max_brightness,
            self.step,
            self.fps,
        )

        self._breathing = False
        self._thread    = None

    @property
    def breathing(self) -> bool:
        return self._breathing

    @breathing.setter
    def breathing(self, new: bool) -> None:
        if not isinstance(new, bool):
            raise TypeError(f'"breathing" must be of type `bool`, not {type(new)}')

        if self.breathing and not new:
            self.stop()
        elif not self.breathing and new:
            self.start()

        self._breathing = new


    @property
    def controller(self) -> 'LEDMatrixController':
        """
        The controller for the LED matrix device.
        """
        return self._controller

    @controller.setter
    @freeze_setter()
    def controller(self, new):
        from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
        if not isinstance(new, LEDMatrixController):
            raise TypeError(f'controller must be LEDMatrixController, not {type(new)}')

        self._controller = new

    @property
    def initial_brightness(self) -> int:
        """

        .. note::
            This is a read-only property.
        """
        return self.__initial_brightness

    @property
    def min_brightness(self) -> int:
        """
        The minimum LED brightness in the cycle.
        """
        return self._min_brightness

    @min_brightness.setter
    def min_brightness(self, new):
        if not isinstance(new, int):
            raise TypeError('"min_brightness" must be int')
        if not 0 <= new <= 100:
            raise ValueError('"min_brightness" must be between 0 and 100')
        if self._max_brightness is not None and new > self._max_brightness:
            raise ValueError('"min_brightness" must be <= max_brightness')

        self._min_brightness = new

    @property
    def max_brightness(self) -> int:
        """
        The maximum LED brightness in the cycle.
        """
        return self._max_brightness

    @max_brightness.setter
    def max_brightness(self, new):
        if not isinstance(new, int):
            raise TypeError('"max_brightness" must be int')
        if not 0 <= new <= 100:
            raise ValueError('"max_brightness" must be between 0 and 100')
        if self._min_brightness is not None and new < self._min_brightness:
            raise ValueError('"max_brightness" must be >= min_brightness')

        self._max_brightness = new

    @property
    def step(self) -> int:
        """
        Amount to change brightness each tick.
        """
        return self._step

    @step.setter
    def step(self, new):
        if not isinstance(new, int):
            raise TypeError('"step" must be int')
        if new <= 0 or new > 100:
            raise ValueError('"step" must be > 0 and <= 100')

        self._step = new

    @property
    def fps(self) -> float:
        """
        Frames per second for the breathing effect.
        """
        return self._fps

    @fps.setter
    def fps(self, new):
        if not isinstance(new, (int, float)):
            raise TypeError('"fps" must be a number')
        if new <= 0:
            raise ValueError('"fps" must be > 0')

        self._fps = float(new)

    def _breath_loop(self):
        interval = 1.0 / self._fps
        current = max(self._min_brightness, min(self.controller.brightness, self._max_brightness))
        going_up = True

        def next_brightness(curr, up):
            """Calculate next brightness value and direction."""
            if up:
                self.method_logger.debug("Getting next brightness value (up=%s)", up)
                next_val = curr + self._step
                if next_val >= self._max_brightness:
                    return self._max_brightness, False
                return next_val, True
            else:
                self.method_logger.debug("Getting next brightness value (up=%s)", up)
                next_val = curr - self._step
                if next_val <= self._min_brightness:
                    return self._min_brightness, True
                return next_val, False

        while self._breathing:
            # Handle pause
            if self._pause_event.is_set():
                self.method_logger.debug("Breathing paused, sleeping")
                time.sleep(interval)
                continue

            # Update brightness
            current, going_up = next_brightness(current, going_up)
            self.controller.brightness = current

            time.sleep(interval)

    def start(self):
        """
        Begin the breathing effect in a background daemon thread.
        No effect if already running.
        """
        self.method_logger.debug('Starting breathing effect')

        if not self._breathing:
            self._breathing = True
            self._thread = threading.Thread(target=self._breath_loop, daemon=True)
            self._thread.start()

        self.method_logger.debug('Breathing effect started')

    def stop(self):
        """
        Stop the breathing effect and wait for the thread to finish.
        """
        self._breathing = False
        if self._thread:
            self._thread.join()
            self._thread = None

        self.method_logger.debug('Breathing effect stopped')
        self.method_logger.debug(f'Setting brightness to initial value {self.initial_brightness}.')
        self.controller.brightness = self.initial_brightness
