from __future__ import annotations
from typing import Optional, Dict, Any
import threading
from aliaser import alias, Aliases
from serial.tools.list_ports_common import ListPortInfo
from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized
from is_matrix_forge.led_matrix.commands.map import CommandVals
from is_matrix_forge.led_matrix.hardware import send_command
from is_matrix_forge.led_matrix.constants import SLOT_MAP
from is_matrix_forge.led_matrix.display.text import show_string as _show_string_raw
from is_matrix_forge.log_engine import ROOT_LOGGER


COMMANDS = CommandVals


class DeviceBase(Aliases):
    """
    Base mixin that stores the underlying serial device and thread-safety knobs.

    Attributes:
        device (ListPortInfo): The serial device to control.
        thread_safe (bool): Enables use of an internal RLock for synchronized ops.
        cmd_lock (Optional[threading.RLock]): Lazily created lock when thread_safe.
    """
    def __init__(self, *, device: ListPortInfo, thread_safe: bool = False, **kwargs: Any) -> None:
        # Initialize core device/threading state BEFORE forwarding to super(), so
        # downstream mixins (e.g., brightness/breather/identify) can safely access
        # self.device during their initialization.
        if not device:
            raise ValueError('device cannot be None or empty.')
        self._device: ListPortInfo = device
        self._thread_safe: bool = bool(thread_safe)
        self._cmd_lock: Optional[threading.RLock] = None
        # Cooperative init: forward any remaining kwargs down the MRO chain
        super().__init__(**kwargs)

    # ——— device/meta ———
    @property
    def device(self) -> ListPortInfo:
        return self._device

    @property
    def thread_safe(self) -> bool:
        return self._thread_safe

    @property
    def cmd_lock(self) -> Optional[threading.RLock]:
        if self._cmd_lock is None and self.thread_safe:
            self._cmd_lock = threading.RLock()
        return self._cmd_lock

    # ——— status helpers ———
    @property
    def animating(self) -> bool:
        res = send_command(dev=self.device, command=COMMANDS.Animate, with_response=True)
        return bool(res and res[0])

    @property
    def location(self) -> Dict[str, Any]:
        return SLOT_MAP.get(self.device.location)

    @property
    def location_abbrev(self) -> str:
        return self.location['abbrev']

    @property
    @alias('serial_port', 'port_name')
    def name(self) -> str:
        return self.device.name

    @property
    def serial_number(self) -> str:
        return self.device.serial_number

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

    def _ping(self) -> None:
        try:
            _ = self.animating
        except Exception:
            pass

    # ——— tiny display helpers (neutral) ———
    @synchronized
    def display_location(self) -> None:
        _show_string_raw(self.device, self.location_abbrev)

    @synchronized
    def display_name(self) -> None:
        _show_string_raw(self.device, self.name)

