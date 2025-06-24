"""
Hardware communication module for LED Matrix.

This module provides low-level functions for communicating with LED matrix hardware.
It includes functions for sending commands, controlling brightness, and other basic operations.
"""

from is_matrix_forge.led_matrix.commands import send_command
from is_matrix_forge.led_matrix.commands.map import CommandVals

from enum import IntEnum


# Import the necessary functions from the controller module


class Game(IntEnum):
    Snake = 0x00
    Pong = 0x01
    Tetris = 0x02
    GameOfLife = 0x03


class GameOfLifeStartParam(IntEnum):
    Currentmatrix = 0x00
    Pattern1 = 0x01
    Blinker = 0x02
    Toad = 0x03
    Beacon = 0x04
    Glider = 0x05

    def __str__(self):
        return self.name.lower()

    def __repr__(self):
        return str(self)

    @staticmethod
    def argparse(s):
        try:
            return GameOfLifeStartParam[s.lower().capitalize()]
        except KeyError:
            return s


class GameControlVal(IntEnum):
    Up = 0
    Down = 1
    Left = 2
    Right = 3
    Quit = 4


def disconnect_dev(dev):
    """
    Disconnect the device from the system.

    Parameters:
        dev (str):
            The device to disconnect.
    """
    global DISCONNECTED_DEVS
    if dev in DISCONNECTED_DEVS:
        return
    DISCONNECTED_DEVS.append(dev)


def bootloader_jump(dev):
    """Reboot into the bootloader to flash new firmware"""
    send_command(dev, CommandVals.BootloaderReset, [0x00])


def get_version(dev):
    """Get the device's firmware version"""
    res = send_command(dev, CommandVals.Version, with_response=True)
    if not res:
        return 'Unknown'
    major = res[0]
    minor = (res[1] & 0xF0) >> 4
    patch = res[1] & 0xF
    pre_release = res[2]

    version = f"{major}.{minor}.{patch}"
    if pre_release:
        version += " (Pre-release)"
    return version


def send_serial(dev, s, command):
    """Send serial command by using existing serial connection"""
    try:
        s.write(command)
    except (IOError, OSError) as _ex:
        disconnect_dev(dev.device)
        # print("Error: ", ex)


def get_pwm_freq(dev):
    """Adjust the brightness scaling of the entire screen."""
    res = send_command(dev, CommandVals.PwmFreq, with_response=True)
    freq = int(res[0])
    if freq == 0:
        return 29000
    elif freq == 1:
        return 3600
    elif freq == 2:
        return 1800
    elif freq == 3:
        return 900
    else:
        return None


def pwm_freq(dev, freq):
    """Set the PWM frequency"""
    if freq == "29kHz":
        send_command(dev, CommandVals.PwmFreq, [0])
    elif freq == "3.6kHz":
        send_command(dev, CommandVals.PwmFreq, [1])
    elif freq == "1.8kHz":
        send_command(dev, CommandVals.PwmFreq, [2])
    elif freq == "900Hz":
        send_command(dev, CommandVals.PwmFreq, [3])


def define_controllers(threaded=False):
    from is_matrix_forge.led_matrix.controller.helpers import get_controllers
    return get_controllers(threaded)


# CONTROLLERS = define_controllers()


def brightness(dev, b: int):
    """Adjust the brightness scaling of the entire screen."""
    send_command(dev, CommandVals.Brightness, [b])


def get_brightness(dev):
    """Retrieve the current brightness value."""
    res = send_command(dev, CommandVals.Brightness, with_response=True)
    return int(res[0])


def animate(dev, b: bool):
    """Enable or disable animation."""
    send_command(dev, CommandVals.Animate, [0x01 if b else 0x00])


def get_animate(dev):
    """Check if animation is enabled."""
    res = send_command(dev, CommandVals.Animate, with_response=True)
    return bool(res[0])


def percentage(dev, p):
    """Fill a percentage of the screen from bottom to top."""
    from is_matrix_forge.inputmodule import PatternVals

    send_command(dev, CommandVals.Pattern, [PatternVals.Percentage, p])



