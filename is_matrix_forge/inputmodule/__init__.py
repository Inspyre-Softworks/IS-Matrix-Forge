from is_matrix_forge.led_matrix.commands.map import CommandVals
from is_matrix_forge.led_matrix.constants import (
    DISCONNECTED_DEVS,
    FWK_MAGIC,
    PID as LED_MATRIX_PID,
    RESPONSE_SIZE,
    VID as FWK_VID,
)
from is_matrix_forge.led_matrix.display.patterns.built_in.stencils.res import PatternVals
from is_matrix_forge.led_matrix.hardware import (
    Game,
    GameControlVal,
    GameOfLifeStartParam,
    bootloader_jump,
    brightness,
    get_brightness,
    get_version,
    send_command,
    send_command_raw,
)
from is_matrix_forge.led_matrix.helpers import disconnect_dev, send_serial

QTPY_PID = 0x001F
INPUTMODULE_PIDS = [LED_MATRIX_PID, QTPY_PID]
