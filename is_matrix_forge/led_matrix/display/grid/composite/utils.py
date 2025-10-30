from is_matrix_forge.led_matrix.display.grid.composite import BackgroundGrid, CompositeGrid, ForegroundGrid
from inspyre_toolbox.syntactic_sweets.classes.decorators.type_validation import validate_type
from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController

from is_matrix_forge.log_engine import ROOT_LOGGER, Loggable

MOD_LOGGER = ROOT_LOGGER.get_child(__name__)


class PercentDisplayScene(Loggable):
    __DEFAULT_BRIGHTNESS = 50
    __DEFAULT_INVERT_ON_OVERLAP = True
    __DEFAULT_MIN_PERCENT_FOR_DIGITS_ON_BOTTOM = 15
    __DEFAULT_MAX_PERCENT_FOR_DIGITS_ON_TOP = 85

    def __init__(
            self,
            brightness=None,
            invert_on_overlap=None,
            max_percent_for_digits_on_top=None,
            min_percent_for_digits_on_bottom=None,
            controller=None
    ):
        super().__init__(MOD_LOGGER)
        self.__last_scene = None

        # Set `provisioned` flag to False.
        self.__provisioned = False

        self.__controller = None

        # Set up placeholders for our composite and its constituent grids;

        # We'll build the scene in `build` and draw the composite in the
        # `redraw` method.

        self.__composite  = None
        self.__background = None
        self.__foreground = None

        # Create some placeholders for our settings.
        #
        # These will be set in `__provision__`;
        self.__brightness                       = None
        self.__invert_on_overlap                = None
        self.__max_percent_for_digits_on_top    = None
        self.__min_percent_for_digits_on_bottom = None

        self.class_logger.debug('Initializing PercentDisplayScene')

        # Provision our settings.
        self.__provision__(
            brightness=brightness,
            invert_on_overlap=invert_on_overlap,
            max_percent_for_digits_on_top=max_percent_for_digits_on_top,
            min_percent_for_digits_on_bottom=min_percent_for_digits_on_bottom,
        )

        self.class_logger.debug('PercentDisplayScene initialized')

        if not self.provisioned:
            self.class_logger.error('Error provisioning PercentDisplayScene')
            raise ValueError('PercentDisplayScene not provisioned')

        if self.percent and self.controller:
            self.class_logger.debug(f'Building scene for {self.percent}% and drawing to controller {self.controller}')
            self.build_scene()
            self.draw()
        else:
            self.class_logger.debug('PercentDisplayScene not built or drawn')

    def __provision__(
            self,
            brightness=None,
            invert_on_overlap=None,
            max_percent_for_digits_on_top=None,
            min_percent_for_digits_on_bottom=None
    ):
        log = self.method_logger
        log.debug('Provisioning PercentDisplayScene')

        self.brightness = brightness or self.__DEFAULT_BRIGHTNESS
        self.invert_on_overlap = invert_on_overlap or self.__DEFAULT_INVERT_ON_OVERLAP
        self.max_percent_for_digits_on_top = max_percent_for_digits_on_top or  self.__DEFAULT_MAX_PERCENT_FOR_DIGITS_ON_TOP
        self.min_percent_for_digits_on_bottom = min_percent_for_digits_on_bottom or self.__DEFAULT_MIN_PERCENT_FOR_DIGITS_ON_BOTTOM

        log.debug(f'PercentDisplayScene provisioned with the following settings: {self.current_settings}')

        self.__provisioned = True

    @property
    def background(self):
        """
        The background grid for the composite scene. This will contain your dynamic percent-bar.

        Returns:
            BackgroundGrid:
                The background grid for the composite scene.
        """
        return self.__background

    @property
    def brightness(self):
        return self.__brightness

    @brightness.setter
    @validate_type(int, float, str, preferred_type=int)
    def brightness(self, new):
        self.__brightness = int(new)

    @property
    def composite(self):
        """
        The composite grid for the scene. This will contain your static percent-bar and dynamic digits.

        Returns:
            CompositeGrid:
                The composite grid for the scene.
        """
        return self.__composite

    @property
    def controller(self) -> 'LEDMatrixController':
        return self.__controller

    @controller.setter
    @validate_type(LEDMatrixController)
    def controller(self, new):
        self.__controller = new

    @property
    def current_settings(self):
        """
        The current settings for the scene. Read-only.

        Returns:
            dict:
                A dictionary containing the settings for the scene.
        """
        return {
            'brightness': self.brightness or self.__DEFAULT_BRIGHTNESS,
            'invert_on_overlap': self.invert_on_overlap or self.__DEFAULT_INVERT_ON_OVERLAP,

            'max_percent_for_digits_on_top': self.max_percent_for_digits_on_top or
                                             self.__DEFAULT_MAX_PERCENT_FOR_DIGITS_ON_TOP,

            'min_percent_for_digits_on_bottom': self.min_percent_for_digits_on_bottom or
                                                self.__DEFAULT_MIN_PERCENT_FOR_DIGITS_ON_BOTTOM,
        }

    @property
    def default_settings(self):
        """
        The default settings for this scene. Read-only.

        Returns:
            dict[str, Any]:
                A dictionary containing the default settings.
        """
        return {
            'brightness': self.__DEFAULT_BRIGHTNESS,
            'invert_on_overlap': self.__DEFAULT_INVERT_ON_OVERLAP,
        }

    @property
    def foreground(self):
        """
        The foreground grid for the composite scene. This will contain your dynamic digits.

        Returns:
            ForegroundGrid:
                The foreground grid for the composite scene.
        """
        return self.__foreground

    @property
    def invert_on_overlap(self):
        return self.__invert_on_overlap

    @invert_on_overlap.setter
    @validate_type(bool)
    def invert_on_overlap(self, new):
        self.__invert_on_overlap = new

    @property
    def max_percent_for_digits_on_top(self):
        return self.__max_percent_for_digits_on_top

    @max_percent_for_digits_on_top.setter
    @validate_type(int, float, str, preferred_type=int)
    def max_percent_for_digits_on_top(self, new):
        self.__max_percent_for_digits_on_top = int(new)

    @property
    def min_percent_for_digits_on_bottom(self):
        return self.__min_percent_for_digits_on_bottom

    @min_percent_for_digits_on_bottom.setter
    @validate_type(int, float, str, preferred_type=int)
    def min_percent_for_digits_on_bottom(self, new):
        self.__min_percent_for_digits_on_bottom = int(new)

    @property
    def last_scene(self):
        return self.__last_scene

    @property
    def percent(self):
        return self.__percent

    @property
    def provisioned(self):
        return self.__provisioned

    def build_scene(self, percent=None):
        if not self.provisioned:
            raise ValueError("Scene is not provisioned.")

        if percent is None:
            raise ValueError("Percent is required.")

        self.__background = BackgroundGrid()
        self.background.fill_bar(percent)

        on_bottom = False

        if percent > self.max_percent_for_digits_on_top:
            on_bottom = True

        self.__foreground = ForegroundGrid()
        self.foreground.draw_digits(percent, bottom_of_grid=on_bottom)

        self.__composite = CompositeGrid(
            background=self.__background,
            foreground=self.__foreground,
            invert_on_overlap=self.invert_on_overlap,
        )

    def draw(self, controller):
        if not self.provisioned:
            raise ValueError("Scene is not provisioned.")

        if self.composite is None:
            raise ValueError("Scene is not built.")

        if self.composite == self.__last_scene:
            return

        print(self.__last_scene)


        self.composite.draw(controller)

        self.__last_scene = self.composite

    def redraw(self, percent, controller):
        self.build_scene(percent)
        self.draw(controller)
