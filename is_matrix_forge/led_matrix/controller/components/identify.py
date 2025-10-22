from __future__ import annotations
import logging
from time import sleep
from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized
from is_matrix_forge.led_matrix.display.text import show_string as _show_string_raw


LOGGER = logging.getLogger(__name__)


class IdentifyManager:
    def __init__(self, *, skip_greeting: bool = False, skip_identify: bool = False,
                 skip_all_init_animations: bool = False, **kwargs):
        super().__init__(**kwargs)
        if skip_all_init_animations:
            LOGGER.info('Skipping all initialization animations')

        if not (skip_greeting or skip_all_init_animations):
            self._greet()

        if not (skip_identify or skip_all_init_animations):
            self.identify()

    def _greet(self):
        # cheap, safe default
        from is_matrix_forge.led_matrix.display.text import show_string as _show
        _show(self.device, 'Hello')

    @synchronized
    def identify(self, *, skip_clear: bool = False, duration: float = 20.0, cycles: int = 3) -> None:
        # Validate arguments to prevent division by zero or negative intervals
        if not isinstance(cycles, int) or cycles <= 0:
            raise ValueError('cycles must be a positive integer')
        if duration <= 0:
            raise ValueError('duration must be a positive number')
        if not skip_clear and hasattr(self, 'clear_matrix'):
            self.clear_matrix()
        messages = (self.location_abbrev, self.device.name)
        interval = duration / (cycles * len(messages))
        for _ in range(cycles):
            for msg in messages:
                _show_string_raw(self.device, msg)
                sleep(interval)
        if not skip_clear and hasattr(self, 'clear_matrix'):
            self.clear_matrix()

