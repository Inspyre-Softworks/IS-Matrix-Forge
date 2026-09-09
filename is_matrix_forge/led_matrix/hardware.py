"""
Hardware communication module for LED Matrix.

This module provides low-level functions for communicating with LED matrix hardware.
It includes functions for sending commands, controlling global brightness, and
atomically staging complete per-LED grayscale framebuffers.
"""
from enum import IntEnum
from collections.abc import Sequence
from typing import List, Optional, ByteString, Union

import serial
from serial.tools.list_ports_common import ListPortInfo

from is_matrix_forge.led_matrix.commands.map import CommandVals
from is_matrix_forge.led_matrix.display.patterns.built_in.stencils.res import PatternVals

from is_matrix_forge.led_matrix.constants import (
    DEFAULT_BAUDRATE,
    RESPONSE_SIZE,
    FWK_MAGIC,
    WIDTH,
    HEIGHT,
)
from is_matrix_forge.led_matrix.helpers import disconnect_dev

from is_matrix_forge.log_engine import ROOT_LOGGER


MOD_LOGGER = ROOT_LOGGER.get_child('led_matrix.hardware')

del ROOT_LOGGER

FRAMEBUFFER_SIZE = WIDTH * HEIGHT


def normalize_framebuffer_brightness_grid(
    grid: Sequence[Sequence[int]],
) -> List[List[int]]:
    """Validate and copy a column-major 9×34 raw brightness framebuffer."""
    if isinstance(grid, (str, bytes, bytearray)) or not isinstance(grid, Sequence):
        raise TypeError('brightness grid must be a sequence of columns')
    if len(grid) != WIDTH:
        raise ValueError(f'brightness grid must contain exactly {WIDTH} columns')

    normalized: List[List[int]] = []
    for x, column in enumerate(grid):
        if isinstance(column, (str, bytes, bytearray)) or not isinstance(column, Sequence):
            raise TypeError(f'brightness column {x} must be a sequence')
        if len(column) != HEIGHT:
            raise ValueError(
                f'brightness column {x} must contain exactly {HEIGHT} values'
            )

        normalized_column: List[int] = []
        for y, value in enumerate(column):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f'brightness at ({x}, {y}) must be an integer from 0 to 255'
                )
            if not 0 <= value <= 255:
                raise ValueError(
                    f'brightness at ({x}, {y}) must be between 0 and 255'
                )
            normalized_column.append(value)
        normalized.append(normalized_column)
    return normalized


def _write_serial_packet(stream, packet: Sequence[int]) -> None:
    """Write one complete packet or raise if the serial stream writes partially."""
    payload = bytes(packet)
    written = stream.write(payload)
    if written is not None and written != len(payload):
        raise IOError(f'Only wrote {written} of {len(payload)} framebuffer bytes')


def stage_framebuffer_brightness_column(
    stream,
    x: int,
    values: Sequence[int],
) -> None:
    """Stage one complete 34-pixel grayscale column on an open serial stream."""
    if isinstance(x, bool) or not isinstance(x, int):
        raise TypeError('column index must be an integer')
    if not 0 <= x < WIDTH:
        raise IndexError(f'column index must be between 0 and {WIDTH - 1}')
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError('brightness column must be a sequence')
    if len(values) != HEIGHT:
        raise ValueError(f'brightness column must contain exactly {HEIGHT} values')

    column = normalize_framebuffer_brightness_grid(
        [[0] * HEIGHT if col != x else values for col in range(WIDTH)]
    )[x]
    _write_serial_packet(
        stream,
        FWK_MAGIC + [CommandVals.StageGreyCol, x] + column,
    )


def commit_framebuffer_brightness(stream) -> None:
    """Atomically display the columns currently in the firmware staging buffer."""
    _write_serial_packet(
        stream,
        FWK_MAGIC + [CommandVals.DrawGreyColBuffer, 0x00],
    )


def set_framebuffer_brightness(
    dev: ListPortInfo,
    grid: Sequence[Sequence[int]],
) -> None:
    """Display a complete raw per-LED brightness framebuffer atomically.

    ``grid`` is column-major (``grid[x][y]``), with 9 columns, 34 rows, and
    integer brightness values from 0 through 255.
    """
    normalized = normalize_framebuffer_brightness_grid(grid)
    try:
        with serial.Serial(str(dev.device), DEFAULT_BAUDRATE) as stream:
            for x, column in enumerate(normalized):
                stage_framebuffer_brightness_column(stream, x, column)
            commit_framebuffer_brightness(stream)
    except (IOError, OSError):
        disconnect_dev(dev.device)
        raise

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


def get_framebuffer_brightness(dev) -> List[int]:
    """Return the framebuffer brightness as a flat list of length ``FRAMEBUFFER_SIZE``."""
    res = send_command(
        dev,
        CommandVals.GetAllBrightness,
        with_response=True,
        response_size=FRAMEBUFFER_SIZE,
        response_timeout=1.0,
    )
    if not res:
        raise IOError('No data returned for framebuffer brightness request.')
    if len(res) < FRAMEBUFFER_SIZE:
        raise IOError(
            f'Expected {FRAMEBUFFER_SIZE} brightness bytes, received {len(res)}.'
        )
    return list(res[:FRAMEBUFFER_SIZE])


def _reshape_flat_to_grid(flat: List[int], width: int, height: int) -> List[List[int]]:
    if len(flat) != width * height:
        raise ValueError('Flat list size does not match width * height')
    return [flat[i * width:(i + 1) * width] for i in range(height)]


def get_framebuffer_brightness_grid(dev) -> List[List[int]]:
    """Return framebuffer brightness as a ``height × width`` grid."""
    flat = get_framebuffer_brightness(dev)
    return _reshape_flat_to_grid(flat, WIDTH, HEIGHT)


def animate(dev, b: bool):
    """Enable or disable animation."""
    send_command(dev, CommandVals.Animate, [0x01 if b else 0x00])


def get_animate(dev):
    """Check if animation is enabled."""
    res = send_command(dev, CommandVals.Animate, with_response=True)
    return bool(res[0])


def percentage(dev, p):
    """Fill a percentage of the screen from bottom to top."""

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
        log = MOD_LOGGER.get_child('send_serial')
        log.debug(f'Integer bytes: {list(cmd_bytes)}')
        log.debug(f"Hex bytes:    {[f'0x{b:02X}' for b in cmd_bytes]}")
        log.debug(f'Raw bytes:    {cmd_bytes!r}')

    try:
        with serial.Serial(str(controller.device), baud) as ser:
            ser.write(cmd_bytes)
    except (IOError, OSError) as _ex:
        disconnect_dev(controller.device)


def send_command_raw(
    dev: ListPortInfo,
    command: List[int],
    with_response: bool = False,
    response_size: Optional[int] = None,
    response_timeout: Optional[float] = None,
) -> Optional[ByteString]:
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
    timeout = response_timeout if with_response else None
    if timeout is None and with_response:
        timeout = 1.0
    try:
        with serial.Serial(str(dev.device), 115200, timeout=timeout) as s:
            s.write(cmd_bytes)
            if not with_response:
                return None

            if timeout is not None:
                s.timeout = timeout
            return s.read(res_size)
    except (IOError, OSError) as _ex:
        disconnect_dev(dev.device)
        return None
        # print("Error: ", ex)


def send_command(
        dev:           ListPortInfo,
        command:       int,
        parameters:    Optional[List[int]] = None,
        with_response: bool                = False,
        response_size: Optional[int]       = None,
        response_timeout: Optional[float]  = None,
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

        response_size (Optional[int], optional):
            Number of bytes to read when awaiting a response. Defaults to
            :data:`is_matrix_forge.led_matrix.constants.RESPONSE_SIZE`.

        response_timeout (Optional[float], optional):
            How long to wait for a response before giving up. Defaults to 1s
            when a response is requested.

    Returns:
        Optional[ByteString]:
            The response from the device, if any, or None if no response or an error occurred.
    """
    if parameters is None:
        parameters = []
    return send_command_raw(
        dev,
        FWK_MAGIC + [command] + parameters,
        with_response,
        response_size=response_size,
        response_timeout=response_timeout,
    )
