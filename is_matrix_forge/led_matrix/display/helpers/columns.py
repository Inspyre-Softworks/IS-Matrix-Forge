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
from is_matrix_forge.led_matrix.commands.map import CommandVals
from is_matrix_forge.led_matrix.constants import FWK_MAGIC
from is_matrix_forge.led_matrix.hardware import send_serial, send_command
from is_matrix_forge.log_engine import ROOT_LOGGER


MOD_LOGGER = ROOT_LOGGER.get_child('led_matrix.display.helpers.columns')


def send_col(dev, x, vals):
    log = MOD_LOGGER.get_child('send_col')
    """Stage greyscale values for a single column. Must be committed with commit_cols()"""
    command = FWK_MAGIC + [CommandVals.StageGreyCol, x] + vals
    log.debug(f'Sending command: {command}')
    send_command(dev, *command)


def commit_cols(dev, s):
    """Commit the changes from sending individual cols with send_col(), displaying the matrix.
    This makes sure that the matrix isn't partially updated."""
    command = FWK_MAGIC + [CommandVals.DrawGreyColBuffer, 0x00]
    send_serial(dev, s, command)
