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
import threading


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
    def __init__(self, device, *, thread_safe: bool = False, parent_log_device=MOD_LOGGER, **kwargs):
        """
        Concrete controller wiring together all mixins and the device base.

        Parameters:
            device: The serial device (pyserial ListPortInfo) to control.
            thread_safe (bool): Enable internal locking for cross-thread calls.
            parent_log_device: Logger to attach to this controller.
            **kwargs: Passed through to mixin initializers.
        """
        # Initialize logging first (compatible with inspy_logger’s Loggable)
        Loggable.__init__(self, parent_log_device=parent_log_device)

        # Initialize device + threading metadata first
        DeviceBase.__init__(self, device=device, thread_safe=thread_safe)
        # Mark owning thread and enable misuse warnings for the synchronized decorator
        self._owner_thread_id = threading.get_ident()
        self._warn_on_thread_misuse = True
        # Ensure command lock exists when thread safety requested
        if thread_safe:
            _ = self.cmd_lock

        # Use a cooperative super() chain starting after Loggable to init
        # other mixins in MRO up through BrightnessManager (which currently
        # does not call super()).
        super(Loggable, self).__init__(
            device=device,
            thread_safe=thread_safe,
            **kwargs
        )

        # Ensure BreatherManager is initialized (it relies on super to reach
        # DeviceBase, so pass device/thread_safe to be safe). Initialize it
        # after others so synchronized() can pause around subsequent calls.
        BreatherManager.__init__(
            self,
            device=device,
            thread_safe=thread_safe,
            **kwargs
        )

    def __repr__(self) -> str:
        try:
            name = getattr(self.device, 'name', '<unknown>')
        except Exception:
            name = '<unknown>'
        return f"{self.__class__.__name__}({name})"
