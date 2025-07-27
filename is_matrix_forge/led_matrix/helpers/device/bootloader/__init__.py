import platform
import psutil

from inspyre_toolbox.exceptional import CustomRootException


class UnsupportedOSError(CustomRootException):
    """
    Raised when we have no function for finding the bootloader drive on the current platform.
    """
    def __init__(self):
        super().__init__("Unsupported platform for bootloader search")


if platform.system() == 'Windows':
    from is_matrix_forge.led_matrix.helpers.device.bootloader.win import find_bootloader_drive
elif platform.system() in ['Linux', 'Darwin']:
    from is_matrix_forge.led_matrix.helpers.device.bootloader.unix import find_bootloader_drive
else:
    raise UnsupportedOSError()


class RP2BootloaderMixin:
    BOOTLOADER_LABEL = "RPI-RP2"
    BOOTLOADER_VID = 0x2E8A
    BOOTLOADER_PID = 0x0003

    def find_bootloader_drive(self):
        """
        Cross-platform search for the RPI-RP2 mass storage drive.
        Returns the mount point (Windows: 'E:\\', Linux: '/media/user/RPI-RP2', Mac: '/Volumes/RPI-RP2'), or None if not found.
        """
        system = platform.system()
        for part in psutil.disk_partitions(all=False):
            try:
                if system == "Windows":
                    # On Windows, volume label is available via psutil
                    if part.opts and 'cdrom' in part.opts:
                        continue  # skip cdrom
                    label = self._get_volume_label_win(part.device)
                    if label == self.BOOTLOADER_LABEL:
                        return part.mountpoint
                elif self.BOOTLOADER_LABEL in part.mountpoint:
                    return part.mountpoint
            except Exception:
                continue
        return None
