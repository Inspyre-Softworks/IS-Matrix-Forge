"""


Author: 
    Inspyre Softworks

Project:
    led-matrix-battery

File: 
    is_matrix_forge/led_matrix/utils/base.py
 

Description:
    

"""
import serial

from is_matrix_forge.led_matrix import RESPONSE_SIZE, disconnect_dev, FWK_MAGIC


def send_command_raw(dev, command, with_response=False):
    """Send a command to the device.
    Opens new serial connection every time"""
    # print(f"Sending command: {command}")
    try:
        with serial.Serial(dev.device, 115200) as s:
            s.write(command)

            if with_response:
                res = s.read(RESPONSE_SIZE)
                # print(f"Received: {res}")
                return res
    except (IOError, OSError) as _ex:
        disconnect_dev(dev.device)
        # print("Error: ", ex)


def send_command(dev, command, parameters=[], with_response=False):
    return send_command_raw(dev, FWK_MAGIC + [command] + parameters, with_response)
