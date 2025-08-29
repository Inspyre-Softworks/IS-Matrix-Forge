from __future__ import annotations
from threading import Thread

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
        try:
            if thread.is_alive():
                thread.join(timeout=timeout)
        except Exception:
            pass

    @staticmethod
    def clear(device_obj) -> None:
        if hasattr(device_obj, 'clear'):
            try:
                device_obj.clear()
            except Exception:
                pass
