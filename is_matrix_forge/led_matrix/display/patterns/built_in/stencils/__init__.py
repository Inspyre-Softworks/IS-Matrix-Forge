"""


Author: 
    Inspyre Softworks

Project:
    led-matrix-battery

File: 
    ${DIR_PATH}/${FILE_NAME}
 

Description:
    $DESCRIPTION

"""
import serial

from is_matrix_forge.led_matrix.constants import WIDTH, HEIGHT
from is_matrix_forge.led_matrix.display.helpers.columns import send_col, commit_cols
from is_matrix_forge.led_matrix.hardware import send_command
from is_matrix_forge.led_matrix.hardware import CommandVals


def all_brightnesses(dev):
    """Increase the brightness with each pixel.
    Only 0-255 available, so it can't fill all 306 LEDs"""
    with serial.Serial(dev.device, 115200) as s:
        for x in range(0, WIDTH):
            vals = [0 for _ in range(HEIGHT)]

            for y in range(HEIGHT):
                brightness = x + WIDTH * y
                if brightness > 255:
                    vals[y] = 0
                else:
                    vals[y] = brightness

            send_col(dev, s, x, vals)
        commit_cols(dev, s)



def every_nth_row(dev, n):
    for x in range(WIDTH):
        vals = [(0xFF if y % n == 0 else 0) for y in range(HEIGHT)]

        send_command(dev, CommandVals.StageGreyCol, [x] + vals)
    send_command(dev, CommandVals.DrawGreyColBuffer, [])


def every_nth_col(dev, n):
    for x in range(WIDTH):
        vals = [(0xFF if x % n == 0 else 0) for _ in range(HEIGHT)]

        send_command(dev, CommandVals.StageGreyCol, [x] + vals)
    send_command(dev, CommandVals.DrawGreyColBuffer, [])


def checkerboard(dev, n):
    for x in range(WIDTH):
        vals = (([0xFF] * n) + ([0x00] * n)) * (HEIGHT // (2 * n))
        if x % (2 * n) < n:
            vals = vals[n:] + vals[:n]
        # Build and send frame command via helper
        send_command(dev, CommandVals.StageGreyCol, [x] + vals)
    # After loop:
    send_command(dev, CommandVals.DrawGreyColBuffer, [])