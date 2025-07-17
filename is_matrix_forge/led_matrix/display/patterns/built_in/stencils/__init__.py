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
    """Increase brightness gradually across the matrix."""
    for x in range(WIDTH):
        vals = [0 for _ in range(HEIGHT)]

        for y in range(HEIGHT):
            brightness = x + WIDTH * y
            vals[y] = brightness if brightness <= 255 else 0

        send_col(dev, x, vals)
    commit_cols(dev)



def every_nth_row(dev, n):
    for x in range(0, WIDTH):
        vals = [(0xFF if y % n == 0 else 0) for y in range(HEIGHT)]

        send_command(dev, CommandVals.StageGreyCol, [x] + vals)
    send_command(dev, CommandVals.DrawGreyColBuffer, [])


def every_nth_col(dev, n):
    for x in range(0, WIDTH):
        vals = [(0xFF if x % n == 0 else 0) for _ in range(HEIGHT)]

        send_command(dev, CommandVals.StageGreyCol, [x] + vals)
    send_command(dev, CommandVals.DrawGreyColBuffer, [])


def checkerboard(dev, n):
    for x in range(WIDTH):
        vals = [
            0xFF if ((x // n) + (y // n)) % 2 == 0 else 0x00
            for y in range(HEIGHT)
        ]
        send_command(dev, CommandVals.StageGreyCol, [x] + vals)
    send_command(dev, CommandVals.DrawGreyColBuffer, [])
