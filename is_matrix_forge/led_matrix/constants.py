"""
Constants for the LED Matrix Battery Monitor.

This module defines various constants used throughout the application, including:
- Serial communication settings (baudrate, response size)
- Hardware identifiers (magic numbers, product ID, vendor ID)
- Matrix dimensions (height, width)
- Grayscale conversion constants for different input sources
- Physical slot mapping for device locations
- Project URLs for external resources
"""
from is_matrix_forge.common.dirs import PRESETS_DIR


# Hardware identifiers
FWK_MAGIC = [0x32, 0xAC]
PID       = 0x20
SN_PREFIX = 'FRAK'
VID       = 0x32AC

# Serial configuration
DEFAULT_BAUDRATE = 115_200
RESPONSE_SIZE    = 32

# Disconnected device placeholder
DISCONNECTED_DEVS = []


# Matrix dimensions
HEIGHT = 34
WIDTH  = 9

# Project URLs
PROJECT_URLS = {
    'github_api': 'https://api.github.com/repos/Inspyre-Softworks/led-matrix-battery/contents'
}

GITHUB_REQ_HEADERS = {"Accept": "application/vnd.github.v3+json"}


# Physical slot mapping
SLOT_MAP = {
    '1-3.2': {'abbrev': 'R1', 'side': 'right', 'slot': 1},
    '1-3.3': {'abbrev': 'R2', 'side': 'right', 'slot': 2},
    '1-4.2': {'abbrev': 'L1', 'side': 'left',  'slot': 1},
    '1-4.3': {'abbrev': 'L2', 'side': 'left',  'slot': 2},
}


from cv2 import COLOR_BGR2GRAY, COLOR_RGB2GRAY
from is_matrix_forge.led_matrix.helpers.device import DEVICES
from is_matrix_forge.common.dirs import APP_DIRS
from is_matrix_forge.dev_tools.presets import MANIFEST_FILE_NAME

MANIFEST_FILE_PATH = PRESETS_DIR.joinpath(MANIFEST_FILE_NAME)

# Grayscale conversion constants
GRAYSCALE_CVT = {
    'camera': COLOR_BGR2GRAY,
    'video': COLOR_RGB2GRAY,
}


# Cleanup
del COLOR_BGR2GRAY, COLOR_RGB2GRAY

__all__ = [
    'APP_DIRS',
    'DEFAULT_BAUDRATE',
    'DEVICES',
    'DISCONNECTED_DEVS',
    'FWK_MAGIC',
    'GITHUB_REQ_HEADERS',
    'GRAYSCALE_CVT',
    'HEIGHT',
    'PID',
    'PROJECT_URLS',
    'RESPONSE_SIZE',
    'SN_PREFIX',
    'SLOT_MAP',
    'VID',
    'WIDTH',
]
