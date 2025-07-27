"""
This module contains the Unix version of `find_bootloader_drive`.
"""
import os
import psutil
from typing import Optional

from is_matrix_forge.led_matrix.helpers.device.bootloader.constants import BOOTLOADER_LABEL


def find_bootloader_drive(label: Optional[str] = None) -> Optional[str]:
    """
    Return the mount point of RPI-RP2 drive on Linux/MacOS, or None.

    Parameters:
        label (str):
            The label of the drive to search for. If None, defaults to `BOOTLOADER_LABEL`.
    """
    if label is None:
        label = BOOTLOADER_LABEL

    for part in psutil.disk_partitions(all=False):
        if label in part.mountpoint:
            return part.mountpoint

    # Fallback
    user = os.environ.get('USER') or os.environ.get('USERNAME')
    possible_mounts = [
        f'/media/{user}/{label}',
        f'/Volumes/{label}'
    ]
    return next((mnt for mnt in possible_mounts if os.path.ismount(mnt)), None)

