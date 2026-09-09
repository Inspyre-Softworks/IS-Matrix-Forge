"""


Author: 
    Inspyre Softworks

Project:
    IS-Matrix-Forge

File: 
    ${DIR_PATH}/${FILE_NAME}
 

Description:
    $DESCRIPTION

"""
from is_matrix_forge.led_matrix.hardware import (
    commit_framebuffer_brightness,
    stage_framebuffer_brightness_column,
)
from is_matrix_forge.log_engine import ROOT_LOGGER


MOD_LOGGER = ROOT_LOGGER.get_child('led_matrix.display.helpers.columns')


def send_col(dev, s, x, vals):
    """Stage greyscale values for a single column. Must be committed with commit_cols()."""
    log = MOD_LOGGER.get_child('send_col')
    log.debug(f'Staging grayscale brightness column {x}')
    stage_framebuffer_brightness_column(s, x, vals)


def commit_cols(dev, s):
    """Commit the changes from sending individual cols with send_col(), displaying the matrix.
    This makes sure that the matrix isn't partially updated."""
    commit_framebuffer_brightness(s)
