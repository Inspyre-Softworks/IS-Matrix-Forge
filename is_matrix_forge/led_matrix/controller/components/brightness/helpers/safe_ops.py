from __future__ import annotations
from threading import Thread
import logging


class SafeOps:
    @staticmethod
    def call(fn) -> None:
        if callable(fn):
            try:
                fn()
            except Exception as e:
                logging.debug(f"Exception in call: {e}", exc_info=True)

    @staticmethod
    def setattr(obj, name: str, value) -> None:
        try:
            setattr(obj, name, value)
        except Exception as e:
            logging.debug(f"Exception in setattr: {e}", exc_info=True)

    @staticmethod
    def join(thread: Thread, *, timeout: float) -> None:
        try:
            if thread.is_alive():
                thread.join(timeout=timeout)
        except Exception as e:
            logging.debug(f"Exception in join: {e}", exc_info=True)

    @staticmethod
    def clear(device_obj) -> None:
        if hasattr(device_obj, 'clear'):
            try:
                device_obj.clear()
            except Exception as e:
                logging.debug(f"Exception in clear: {e}", exc_info=True)
