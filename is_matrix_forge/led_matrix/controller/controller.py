"""
LED Matrix controller wiring together mixin components with the device base.

Key design notes:
- Multiple inheritance uses cooperative initialization via ``super()``.
- ``DeviceBase`` is placed early in the MRO so mixins can safely access ``self.device``.
- ``BrightnessManager`` precedes ``BreatherManager`` in the MRO because the breather
  inspects the controller brightness on initialization.
- ``IdentifyManager`` comes after ``BreatherManager`` because it may call
  ``@synchronized`` methods during ``__init__`` which expect a breather pause context.
- Logging cooperates with an InspyLogger ``Loggable`` when available, but a lightweight
  fallback is supported. The controller passes either ``parent_log_device`` (InspyLogger)
  or ``logger`` (fallback) depending on availability.
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
    DeviceBase,
    KeepAliveManager,
    AnimationManager,
    DrawingManager,
    BrightnessManager,
    BreatherManager,
    IdentifyManager,
):
    def __init__(self, device, *, thread_safe: bool = False, parent_log_device=MOD_LOGGER, **kwargs):
        """
        Concrete controller wiring together all mixins and the device base using a
        single cooperative ``super().__init__`` chain.

        Parameters:
            device: The serial device (pyserial ListPortInfo) to control.
            thread_safe (bool): Enable internal locking for cross-thread calls.
            parent_log_device: Logger to attach to this controller. If the installed
                Loggable expects ``logger`` instead, a fallback path maps it.
            **kwargs: Passed through to mixin initializers. All mixins must call
                ``super().__init__(**kwargs)`` to maintain cooperative initialization.
        """
        # Set thread ownership metadata early for @synchronized misuse checks
        self._owner_thread_id = threading.get_ident()
        self._warn_on_thread_misuse = True

        # Use a single cooperative super() init across all mixins.
        # Prefer the inspy_logger-style kw; fall back to the simple stub.
        try:
            super().__init__(
                device=device,
                thread_safe=thread_safe,
                parent_log_device=parent_log_device,
                **kwargs,
            )
        except TypeError as e:
            if 'parent_log_device' in str(e):
                super().__init__(
                    device=device,
                    thread_safe=thread_safe,
                    logger=parent_log_device,
                    **kwargs,
                )
            else:
                raise

        # Ensure command lock is created if requested
        if thread_safe:
            _ = self.cmd_lock

    def __repr__(self) -> str:
        try:
            name = getattr(self.device, 'name', '<unknown>')
        except Exception:
            name = '<unknown>'
        return f"{self.__class__.__name__}({name})"
