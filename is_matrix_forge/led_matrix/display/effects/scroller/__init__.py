from __future__ import annotations
from typing import TYPE_CHECKING
from is_matrix_forge.common.decorators import freeze_setter


if TYPE_CHECKING:
    from is_matrix_forge.led_matrix.controller import LEDMatrixController


class HardwareScroller:
    """
    This class just manages the native 'animation' for the LED matrix.

    This simply wraps commands to the LED matrix that can;
      - Query the current state of the 'animating' flag
      - Set the 'animating' flag
    """
    def __init__(
            self,
            controller,
            do_not_keep_lit: bool = False
    ):
        self._controller = None
        self.__keep_lit  = None

        self.controller = controller
        self.keep_lit = not do_not_keep_lit

    @property
    def controller(self):
        """
        The controller (therefore the hardware) this scroller is managing.

        Returns:
            The controller object.
        """
        return self._controller

    @controller.setter
    @freeze_setter(allow_reassignment_to_same_value=True)
    def controller(self, new: LEDMatrixController):
        """
        The controller (therefore the hardware) this scroller is managing.

        Parameters:
            new (LEDMatrixController):
                The controller object.

        Returns:
            None

        Raises:
            AssertionError:
                If `new` isn't an instance of :class:`LEDMatrixController`.

        See Also:
            - :func:`~is_matrix_forge.common.decorators.freeze_setter`
            - :meth:`controller`
            - :attr:`controller`
            - :class:`LEDMatrixController`
        """
        from is_matrix_forge.led_matrix import LEDMatrixController
        assert isinstance(new, LEDMatrixController), f"Expected {LEDMatrixController}, got {type(new)}"

        self._controller = new

    @property
    def is_scrolling(self) -> bool:
        """
        Checks if the LED is currently animating (meaning scrolling).

        .. note::
            This is a read-only property.
        """
        return self.controller.animating


    @property
    def keep_lit(self) -> bool:
        """
        Should the LED matrix be kept awake while scrolling?
        """
        return self.__keep_lit

    @keep_lit.setter
    def keep_lit(self, new):
        if not isinstance(new, bool):
            raise TypeError('"keep_lit" must be of type "bool"')
        self.__keep_lit = new

    def start_scrolling(self):
        pass
