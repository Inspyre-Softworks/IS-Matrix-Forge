from easy_exit_calls import ExitCallHandler
from is_matrix_forge.common.decorators import validate_type


ECH = ExitCallHandler()
DEFAULT_TIME_BETWEEN_JIGGLES = 50
MAX_TIME_BETWEEN_JIGGLES     = 59  # Matrix goes to sleep after 60 seconds of command inactivity, so we need to jiggle
                                   # at least once every minute


class MatrixJiggler:
    def __init__(
            self,
            controller    = None,
            interval: int = None,
            do_not_clear_on_stop: bool = False,

    ):
        self._controller        = None
        self.__interval         = None
        self.__last_jiggle_time = None
        self.clear_on_stop      = not do_not_clear_on_stop

        if controller is not None:
            self.controller = controller

    @property
    def controller(self):
        return self._controller

    @controller.setter
    def controller(self, new):
        if new is None:
            raise ValueError("controller cannot be None")
        self._controller = new

    @property
    def interval(self) -> float:
        return self.__interval

    @interval.setter
    @validate_type([float, int], float)
    def interval(self, new):
        self.__interval = new

    def cleanup(self):
        if self.clear_on_stop:
            self.controller.clear()
