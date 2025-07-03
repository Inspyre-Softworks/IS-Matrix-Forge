"""
Hardware communication module for LED Matrix.

This module provides low-level functions for communicating with LED matrix hardware.
It includes functions for sending commands, controlling brightness, and other basic operations.
"""
from enum import IntEnum
from typing import List, Optional, ByteString, Union

import serial
from serial.tools.list_ports_common import ListPortInfo

from is_matrix_forge.led_matrix.commands.map import CommandVals

from is_matrix_forge.led_matrix.constants import RESPONSE_SIZE, FWK_MAGIC
from is_matrix_forge.led_matrix.helpers import disconnect_dev, DISCONNECTED_DEVS

from is_matrix_forge.log_engine import ROOT_LOGGER


MOD_LOGGER = ROOT_LOGGER.get_child('led_matrix.hardware')

del ROOT_LOGGER


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
    """
    Controls for the game controller.
    """
    Up    = 0
    Down  = 1
    Left  = 2
    Right = 3
    Quit  = 4


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


def get_pwm_freq(dev):
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


def send_serial(
    controller: str,
    command: Union[bytes, bytearray, list],
    baud: int = 115200,
    print_debug: bool = True
) -> None:
    """
    Sends raw bytes over serial and prints exactly what is sent.

    Args:
        controller (LEDMatrixController):
            The controller to use.

        command (Union[bytes, bytearray, list]):
            Command as a list of ints, bytes, or bytearray.

        baud (int):
            Baudrate for serial. Defaults to 115200.

        print_debug (bool):
            Whether to print debug info.

    Raises:
        ValueError: If command is not bytes/bytearray/list of ints.
        serial.SerialException: If serial communication fails.
    """
    # Normalize to bytes
    if isinstance(command, (bytes, bytearray)):
        cmd_bytes = bytes(command)
    elif isinstance(command, list):
        cmd_bytes = bytes(command)
    else:
        raise ValueError("Command must be bytes, bytearray, or list of ints")

    if print_debug:
        print(f"[send_serial] Integer bytes: {list(cmd_bytes)}")
        print(f"[send_serial] Hex bytes:    {[f'0x{b:02X}' for b in cmd_bytes]}")
        print(f"[send_serial] Raw bytes:    {cmd_bytes!r}")

    try:
        with serial.Serial(controller.device, baud) as ser:
            ser.write(cmd_bytes)
    except (IOError, OSError) as _ex:
        disconnect_dev(controller.device)


def send_command_raw(dev: ListPortInfo, command: List[int], with_response: bool = False, response_size: Optional[int] = None) -> Optional[ByteString]:
    """
    Send a command to the device using a new serial connection.

    Args:
        dev (ListPortInfo): The device to send the command to.
        command (List[int]): The command to send.
        with_response (bool, optional): Whether to wait for a response from the device. Defaults to False.
        response_size (Optional[int], optional): The size of the response to expect. Defaults to None.

    Returns:
        Optional[ByteString]: The response from the device, if any, or None if no response or an error occurred.

    Raises:
        IOError, OSError: If there is an error communicating with the device.
    """
    cmd_bytes = bytes(command)
    #print(f"Sending command (int): {list(cmd_bytes)}")
    #print(f"Sending command (hex):  {[f'0x{b:02X}' for b in cmd_bytes]}")
    #print(f"Raw bytes: {cmd_bytes!r}")
    res_size = response_size or RESPONSE_SIZE
    try:
        with serial.Serial(dev.device, 115200) as s:
            s.write(cmd_bytes)
            return s.read(res_size) if with_response else None
    except (IOError, OSError) as _ex:
        disconnect_dev(dev.device)
        return None
        # print("Error: ", ex)


def send_command(
        dev:           ListPortInfo,
        command:       int,
        parameters:    Optional[List[int]] = None,
        with_response: bool                = False
) -> Optional[ByteString]:
    """
    Send a command to the device using a new serial connection.

    Parameters:
        dev (ListPortInfo):
            The device to send the command to.

        command (int):
            The command to send.

        parameters (Optional[List[int]], optional):
            The parameters to send with the command. Defaults to None.

        with_response (bool, optional):
            Whether to wait for a response from the device. Defaults to False.

    Returns:
        Optional[ByteString]:
            The response from the device, if any, or None if no response or an error occurred.
    """
    if parameters is None:
        parameters = []
    return send_command_raw(dev, FWK_MAGIC + [command] + parameters, with_response)
