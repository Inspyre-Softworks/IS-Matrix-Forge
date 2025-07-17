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
from is_matrix_forge.led_matrix.hardware import send_command
from is_matrix_forge.log_engine import ROOT_LOGGER


MOD_LOGGER = ROOT_LOGGER.get_child('led_matrix.display.helpers.columns')


def send_col(dev, x, vals):
    log = MOD_LOGGER.get_child('send_col')
    """Stage greyscale values for a single column. Must be committed with commit_cols()"""
    log.debug(f'Sending column {x} with values: {vals}')
    send_command(dev, CommandVals.StageGreyCol, [x] + vals)


def commit_cols(dev):
    """Commit staged columns using the DrawGreyColBuffer command."""
    send_command(dev, CommandVals.DrawGreyColBuffer, [])
