from __future__ import annotations

import threading
from contextlib import nullcontext


class KeepAliveManager:
    """
    A class that manages the keep-alive functionality of the device.
    This class is used to keep the device alive by sending a keep-alive message to the device every `keep_alive_interval` seconds.
    The keep-alive message is sent to the device every `keep_alive_interval` seconds.
    """
    def __init__(self, *, keep_alive_interval: float = 50.0, **kwargs):
        super().__init__(**kwargs)  # cooperative
        self._keep_alive: bool = False
        self._KEEP_ALIVE_INTERVAL: float = float(keep_alive_interval)
        self._keep_alive_thread: threading.Thread | None = None
        self._keep_alive_stop_evt: threading.Event | None = None

    def _keep_alive_worker(self):
        stop_evt = self._keep_alive_stop_evt or threading.Event()
        self._keep_alive_stop_evt = stop_evt
        while not stop_evt.is_set():
            lock_ctx = nullcontext()
            if getattr(self, '_thread_safe', False):
                lock = self.cmd_lock
                if lock is not None:
                    lock_ctx = lock
            with lock_ctx:
                self._ping()
            stop_evt.wait(self._KEEP_ALIVE_INTERVAL)

    @property
    def keep_alive(self) -> bool:
        """
        Get the current state of the keep-alive functionality for the device.

        Returns:
            bool:
                True if the keep-alive functionality is enabled, False otherwise.
        """
        return self._keep_alive

    @keep_alive.setter
    def keep_alive(self, enable: bool):
        """
        Enable or disable the keep-alive functionality of the device.

        Parameters:
            enable (bool):
                True to enable the keep-alive functionality, False to disable it.

        Returns:
            None
        """
        if enable == self._keep_alive:
            return
        if enable:
            self._keep_alive_stop_evt = threading.Event()
            import threading as _t
            self._keep_alive_thread = _t.Thread(
                target=self._keep_alive_worker,
                name=f'{self.__class__.__name__}-KeepAlive-{self.device.name}',
                daemon=True,
            )
            self._keep_alive_thread.start()
            self._keep_alive = True
        else:
            if self._keep_alive_stop_evt is not None:
                self._keep_alive_stop_evt.set()
            if self._keep_alive_thread is not None and self._keep_alive_thread.is_alive():
                self._keep_alive_thread.join(timeout=self._KEEP_ALIVE_INTERVAL + 1)
            self._keep_alive_thread = None
            self._keep_alive_stop_evt = None
            self._keep_alive = False
