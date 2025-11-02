"""
File: monitor.py
Author: Inspyre-Softworks
Description:
    This file contains the PowerMonitor class, which is used to monitor the battery level of the system.
"""
# Standard library imports
from pathlib import Path
from threading import Thread
from typing import Union, Optional

# Third-party imports
from serial.tools.list_ports_common import ListPortInfo

# Inspyre-Softworks imports
from easy_exit_calls import ExitCallHandler

# Package imports
from .errors import *
from .helpers import get_plugged_status
from is_matrix_forge.log_engine import ROOT_LOGGER as PARENT_LOGGER
from is_matrix_forge.notify.sounds import PLUGGED_NOTIFY, UNPLUGGED_NOTIFY

DEFAULT_PLUGGED_SOUND   = PLUGGED_NOTIFY
DEFAULT_UNPLUGGED_SOUND = UNPLUGGED_NOTIFY

ECH = ExitCallHandler()

MOD_LOGGER = PARENT_LOGGER.get_child('monitor')


def run_power_monitor(
        device:                 ListPortInfo,
        battery_check_interval: int = 5,
        plugged_alert:          Optional[Union[str, Path]] = DEFAULT_PLUGGED_SOUND,
        unplugged_alert:        Optional[Union[str, Path]] = DEFAULT_UNPLUGGED_SOUND,
):
    """
    Run the power monitor.

    Parameters:
        device (ListPortInfo):
            The LED matrix on which to display the battery level.

        battery_check_interval (Optional[Union[int, float, str]]):
            The interval (in seconds) at which to check the battery level.

        plugged_alert (Optional[Union[str, Path]]):
            The filepath to the sound to play when the device is plugged into power.

        unplugged_alert (Optional[Union[str, Path]]):
            The filepath to the sound to play when the device is unplugged from power.

    """
    from .monitor import PowerMonitor
    monitor = PowerMonitor(
        device,
        battery_check_interval=battery_check_interval,
        plugged_alert=plugged_alert,
        unplugged_alert=unplugged_alert
    )

    try:
        monitor.start()
    except KeyboardInterrupt:
        monitor.stop(without_salutation=True)

    return monitor
