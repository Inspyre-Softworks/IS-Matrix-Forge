"""
Example template for authoring a controller mixin.

Copy, rename, and adapt this file to add new behavior to the LEDMatrixController.

Usage example:
    from is_matrix_forge.led_matrix.controller.components.example_template import ExampleManager

    class MyController(ExampleManager, ...):
        ...

    ctrl = MyController(device, thread_safe=True)
    ctrl.example_operation("Hello from my mixin!")
"""
from __future__ import annotations

from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized


class ExampleManager:
    """
    Template mixin that demonstrates cooperative initialization and a synchronized
    device operation. Replace with your own fields and methods.
    """

    def __init__(self, *, example_enabled: bool = True, **kwargs):
        # Always call super() to keep the cooperative init chain intact
        super().__init__(**kwargs)
        self._example_enabled = bool(example_enabled)

    @property
    def example_enabled(self) -> bool:
        return self._example_enabled

    @synchronized
    def example_operation(self, message: str = "Hello") -> None:
        """
        Demonstrates a synchronized hardware call (e.g., drawing text).

        This method acquires the controller's lock when thread_safe=True and
        temporarily pauses the breather effect while executing.
        """
        from is_matrix_forge.led_matrix.display.text import show_string as _show
        _show(self.device, str(message))

