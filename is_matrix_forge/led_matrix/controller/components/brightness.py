from __future__ import annotations
from threading import Thread
from time import sleep
from typing import Optional, Union
from is_matrix_forge.common.helpers import percentage_to_value
from is_matrix_forge.led_matrix.hardware import brightness as _set_brightness_raw
from is_matrix_forge.led_matrix.errors import InvalidBrightnessError
from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized


from is_matrix_forge.log_engine import ROOT_LOGGER, Loggable


class BrightnessManager(Loggable):
    FACTORY_DEFAULT_BRIGHTNESS = 75

    def __init__(self, *, default_brightness: Optional[int] = None,
                 skip_init_brightness_set: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._default_brightness = self._norm_pct(
            default_brightness if default_brightness is not None
            else self.FACTORY_DEFAULT_BRIGHTNESS
        )
        self._brightness: Optional[int] = None
        self._set_brightness_on_init = not bool(skip_init_brightness_set)

        if self._set_brightness_on_init:
            self.set_brightness(self._default_brightness)

    @property
    def brightness(self) -> int:
        if self._brightness is None:
            return self._default_brightness

        return self._brightness

    @brightness.setter
    def brightness(self, new: Union[int, float, str]):
        self.set_brightness(new)
        self._brightness = self._norm_pct(new)

    @synchronized
    def fade_out(self, duration: float = 0.33, clear_when_done: bool = False, non_blocking: bool = False) -> None:
        """
        Fade the matrix brightness down to 0 over `duration` seconds.

        Notes:
            - `duration` is total time for the whole fade, not per step.
            - Non-blocking spawns a daemon thread and returns immediately.
        """
        log = MOD_LOGGER.get_child('fade_out')

        start = max(int(getattr(self, 'brightness', 0)), 0)
        if start <= 0:
            log.warning('Cannot fade to 0 if brightness is already 0')
            # Already dark; optionally clear and bounce.
            if clear_when_done:
                self.clear()
            return

        steps = start  # one step per brightness level
        step_delay = duration / steps if duration > 0 else 0.0

        def fader():
            # Walk brightness down to 0 inclusive
            for level in range(start - 1, -1, -1):
                self.set_brightness(level)
                if step_delay > 0:
                    sleep(step_delay)

            # Ensure we're at 0 even if duration was 0
            self.set_brightness(0)

            if clear_when_done:
                self.clear()

        if non_blocking:
            # Start after this method releases the @synchronized lock
            t = Thread(target=fader, name='LED-FadeOut', daemon=True)
            t.start()
            return

        # Blocking path
        fader()


    @synchronized
    def set_brightness(self, brightness: Union[int, float, str]) -> None:
        pct = self._norm_pct(brightness)
        raw = percentage_to_value(max_value=255, percent=pct)
        try:
            _set_brightness_raw(self.device, raw)
        except ValueError as e:
            raise InvalidBrightnessError(raw) from e
        self._brightness = pct

    @staticmethod
    def _norm_pct(val: Union[int, float, str]) -> int:
        if isinstance(val, str):
            val = float(val.strip('%'))
        pct = int(round(float(val)))
        if not (0 <= pct <= 100):
            raise ValueError('Percentage must be between 0 and 100')
        return pct
