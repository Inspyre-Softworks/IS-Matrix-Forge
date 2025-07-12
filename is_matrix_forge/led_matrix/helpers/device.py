"""
Device helper functions for LED matrix hardware.

This module provides utility functions for working with LED matrix devices,
including functions to convert between different device location formats.
"""
from serial import Serial, SerialException
from serial.tools import list_ports
from is_matrix_forge.log_engine import ROOT_LOGGER
from is_matrix_forge.led_matrix.constants import VID as EXPECTED_VID, PID as EXPECTED_PID


MOD_LOGGER = ROOT_LOGGER.get_child('led_matrix.helpers.device')


def serial_loc_to_physical(dev):
    """
    Convert the serial location of a device to its physical location.

    Parameters:
        dev (ListPortInfo):
            The device to convert.

    Returns:
        str:
            The physical location of the device.
    """
    return dev.device


def device_available(device):
    """
    Check if a device is available.

    Parameters:
        device:
            The device to check.

    Returns:
        bool:
            True if the device is available, False otherwise.

    """
    log = MOD_LOGGER.get_child('device_available')
    log.debug(f'Checking if device is available: {device}...')

    if not check_device(device):
        log.warning(f'Device {device} failed check, thus not available.')
        return False
    else:
        log.debug(f'Device {device} is available.')
        return True


def check_device(device):

    from serial.tools.list_ports_common import ListPortInfo

    log = MOD_LOGGER.get_child('check_device')
    log.debug(f'Checking device: {device}...')

    if not isinstance(device, ListPortInfo):
        emsg = f'device must be of type `ListPortInfo`, not {type(device)}'
        log.error(emsg)
        raise TypeError(emsg)

    # Both the vendor and product ID must match to be supported
    if device.vid != EXPECTED_VID or device.pid != EXPECTED_PID:
        log.warning(
            f'Given device is not supported. (VID: {device.vid}, PID: {device.pid})'
        )
        return False

    return bool(test_connection(device.device))


def get_devices():
    log = MOD_LOGGER.get_child('get_devices')

    log.debug('Getting devices...')

    ports = list_ports.comports()

    log.debug(f'Found {len(ports)} devices.')
    log.debug('Filtering and returning devices...')
    return [
        port for port in ports if port.vid == 0x32AC and port.pid == 0x20
    ]


def test_connection(port_name):
    """
    Test the connection to a given port.

    Parameters:
        port_name (str):
            The name of the port to test the: connection to.

    Returns:

    """
    log = MOD_LOGGER.get_child('test_connection')
    log.debug(f'Testing connection to {port_name}...')

    try:
        with Serial(port_name, 115200) as s:
            s.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            s.flush()
            log.debug('Connection test successful.')
            return True
    except SerialException:
        log.debug('Connection test failed.')
        return False


DEVICES = get_devices()

if len(DEVICES) == 0:
    MOD_LOGGER.warning('No devices found. Please connect a device and try again.')
