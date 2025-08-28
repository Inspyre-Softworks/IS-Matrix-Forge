import serial
try:
    from inspyre_toolbox.chrono.sleep import NegateSwitch
except ModuleNotFoundError:  # pragma: no cover - fallback when dependency missing
    class NegateSwitch:
        def __init__(self, initial: bool = False):
            self.value = initial

        def __call__(self, *_):
            self.value = not self.value
            return self.value

try:
    from inspyre_toolbox.path_man import provision_path
except ModuleNotFoundError:  # pragma: no cover - fallback
    from pathlib import Path

    def provision_path(path):
        return Path(path).expanduser().resolve()

from serial.tools.list_ports_common import ListPortInfo
from threading import Thread

import json
from pathlib import Path
from typing import Union, Optional, List, Any, ByteString


DISCONNECTED_DEVS = []


def get_json_from_file(path: Union[str, Path]) -> Any:
    """
    Load and parse a JSON file.

    Args:
        path (Union[str, Path]): The path to the JSON file to load.

    Returns:
        Any: The parsed JSON data.

    Raises:
        FileNotFoundError:
            If the file does not exist.

        IsADirectoryError:
            If the path points to a directory.

        json.JSONDecodeError:
            If the file contains invalid JSON.
    """
    path = provision_path(path)
    if not path.exists():
        raise FileNotFoundError(f'Preset file not found: {path}')

    if not path.is_file():
        raise IsADirectoryError(f'Preset file is a directory: {path}')

    with open(path, 'r') as f:
        return json.load(f)


def load_from_file(
        path:              Union[str, Path],
        expected_width:    Optional[int]               = None,
        expected_height:   Optional[int]               = None,
        fallback_duration: Optional[Union[int, float]] = None
) -> List['Frame']:
    """
    Load a list of frames from a file.

    Args:
        path (Union[str, Path]): The path to the file to load.
        expected_width (Optional[int]): The expected width of the frames in the file. Defaults to 9.
        expected_height (Optional[int]): The expected height of the frames in the file. Defaults to 34.
        fallback_duration (Optional[Union[int, float]]): The duration of the frames in the file. 
            Defaults to 0.33 (1/3 of a second).

    Returns:
        List[Frame]: A list of frames loaded from the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory.
        ValueError: If the file does not contain a valid JSON array.
    """
    from is_matrix_forge.led_matrix.display.animations.frame.helpers import migrate_frame
    from is_matrix_forge.led_matrix.display.grid.helpers import is_valid_grid

    width  = expected_width  or 9
    height = expected_height or 34

    data = get_json_from_file(path)

    if not isinstance(data, list):
        raise ValueError(f"File {path} does not contain a valid JSON array")

    frames = []
    for entry in data:

        if not isinstance(entry, dict) and isinstance(entry, list) and is_valid_grid(entry, width, height):
            entry = migrate_frame(entry, fallback_duration)
            entry['duration'] = fallback_duration or .33

        frames.append(entry)

    return data


def disconnect_dev(dev: str) -> None:
    """
    Disconnect the device from the system.

    Args:
        dev (str): The device to disconnect.

    Note:
        This function adds the device to a global list of disconnected devices
        to prevent further attempts to communicate with it.
    """
    from is_matrix_forge.led_matrix.constants import DISCONNECTED_DEVS
    if dev in DISCONNECTED_DEVS:
        return

    DISCONNECTED_DEVS.append(dev)


def send_serial(dev: ListPortInfo, s: 'serial.Serial', command: ByteString) -> None:
    """
    Send serial command by using an existing serial connection.

    Args:
        dev (ListPortInfo): The device to send the command to.
        s (serial.Serial): The serial connection to use.
        command (ByteString): The command to send.

    Raises:
        IOError, OSError: If there is an error communicating with the device.
    """
    try:
        s.write(command)
    except (IOError, OSError) as _ex:
        disconnect_dev(dev.device)
        # print("Error: ", ex)


def identify_devices(devices: Optional[List[ListPortInfo]] = None) -> None:
    """
    Identify LED matrix devices by flashing an identification message on each
    connected matrix. If no specific devices are provided, all detected devices
    are used.

    Parameters:
        devices (Optional[List[ListPortInfo]], optional):
            List of devices to identify. Defaults to ``None`` which will use all
            detected devices.
    """
    from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController

    if devices is None:
        from is_matrix_forge.led_matrix.helpers.device import DEVICES
        devices = DEVICES

    import logging

    controllers = [LEDMatrixController(dev, 100) for dev in devices]


    def safe_identify(controller):
        try:
            controller.identify()
        except Exception as e:
            logging.exception(f"Exception in identify thread for controller {controller}: {e}")

    threads = []
    for controller in controllers:
        t = Thread(target=safe_identify, args=(controller,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()


running = NegateSwitch(False)
