from __future__ import annotations
from threading import Thread
from is_matrix_forge.common.logging.log_exceptions import log_on_exception


class SafeOps:
    @staticmethod
    def call(fn) -> None:
        if callable(fn):
            try:
                fn()
            except Exception:
                pass

    @staticmethod
    def setattr(obj, name: str, value) -> None:
        try:
            setattr(obj, name, value)
        except Exception:
            pass

    @staticmethod
    def join(thread: Thread, *, timeout: float) -> None:
        if thread.is_alive():
            thread.join(timeout=timeout)

    @staticmethod
    @log_on_exception(level='info')
    def clear(device_obj) -> None:
        if hasattr(device_obj, 'clear'):
            device_obj.clear()
