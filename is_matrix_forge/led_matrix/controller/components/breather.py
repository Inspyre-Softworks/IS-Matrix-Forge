# is_matrix_forge/led_matrix/controller/components/breather.py
from __future__ import annotations
import threading
from time import sleep
from is_matrix_forge.led_matrix.display.effects.breather import Breather


class _BreatherPauseCtx:
    def __init__(self, controller: 'BreatherMixin'):
        self.controller = controller
        self._was_breathing = False

    def __enter__(self):
        b = getattr(self.controller, 'breather', None)
        if b is None:
            return
        if getattr(self.controller, 'breathing', False):
            # avoid joining own thread
            th = getattr(b, '_thread', None)
            if th is threading.current_thread():
                return
            self._was_breathing = True
            self.controller.breathing = False
            sleep(0.05)

    def __exit__(self, exc_type, exc, tb):
        if self._was_breathing:
            self.controller.breathing = True


class BreatherManager:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._breather: Breather | None = Breather(self)

    @property
    def breather(self) -> Breather | None:
        return self._breather

    @property
    def breathing(self) -> bool:
        return bool(self._breather and self._breather.breathing)

    @breathing.setter
    def breathing(self, new: bool):
        if self._breather:
            self._breather.breathing = bool(new)

    def breather_paused(self):
        # synchronized() looks for this
        return _BreatherPauseCtx(self)

