"""
Controller for the LED Matrix.

This file contains the controller for the LED Matrix. The controller is responsible for
managing the different components of the LED Matrix. The components are responsible for
managing the different parts of the LED Matrix. The controller is responsible for
managing
"""
from is_matrix_forge.led_matrix.controller.components.keep_alive import KeepAliveManager
from is_matrix_forge.led_matrix.controller.components.animation import AnimationManager
from is_matrix_forge.led_matrix.controller.components.drawing import DrawingManager
from is_matrix_forge.led_matrix.controller.components.identify import IdentifyManager
from is_matrix_forge.led_matrix.controller.components.brightness import BrightnessManager
from is_matrix_forge.led_matrix.controller.base import DeviceBase
from is_matrix_forge.led_matrix.controller.components.breather import BreatherManager
from is_matrix_forge.log_engine import ROOT_LOGGER, Loggable


MOD_LOGGER = ROOT_LOGGER.get_child(__name__)


class LEDMatrixController(
    Loggable,
    KeepAliveManager,
    AnimationManager,
    DrawingManager,
    IdentifyManager,
    BrightnessManager,
    BreatherManager,
    DeviceBase
):
    def __init__(self, parent_log_device=MOD_LOGGER, **kwargs):
        pass
