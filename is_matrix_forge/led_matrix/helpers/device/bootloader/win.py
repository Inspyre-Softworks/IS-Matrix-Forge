"""
This module contains functions to find the bootloader drive on Windows.
"""
import psutil
from typing import Optional
from is_matrix_forge.led_matrix.helpers.device.bootloader.constants import BOOTLOADER_LABEL


def find_bootloader_drive(self, label: Optional[str] = None) -> Optional[str]:
    if label is None:
        label = BOOTLOADER_LABEL
    """Return the mount point of RPI-RP2 drive on Windows, or None."""
    for part in psutil.disk_partitions(all=False):
        try:
            if part.opts and 'cdrom' in part.opts:
                continue
            label = get_volume_label(part.device)
            if label == BOOTLOADER_LABEL:
                return part.mountpoint
        except Exception:
            continue
    return None


def get_volume_label(device: str) -> str:
    import ctypes
    label = ctypes.create_unicode_buffer(1024)
    fs = ctypes.create_unicode_buffer(1024)
    serial = ctypes.c_ulong()
    maxlen = ctypes.c_ulong()
    flags = ctypes.c_ulong()
    ret = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(device),
        label,
        ctypes.sizeof(label),
        ctypes.byref(serial),
        ctypes.byref(maxlen),
        ctypes.byref(flags),
        fs,
        ctypes.sizeof(fs)
    )
    if ret:
        return label.value
    return ""
