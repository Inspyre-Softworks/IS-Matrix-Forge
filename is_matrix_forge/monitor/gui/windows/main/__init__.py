from .layout import Layout as MainWindowLayout
from ..base import WindowBase
from is_matrix_forge.led_matrix.hardware import brightness
from is_matrix_forge.led_matrix.helpers.device import DEVICES
from is_matrix_forge.monitor.monitor import PowerMonitor
import time


POWER_MONITOR = PowerMonitor(DEVICES[0])


class MainWindow(WindowBase):
    """
    Main window for the LED Matrix Battery Monitor GUI.
    """
    DEFAULT_TITLE = 'LED Matrix Battery Monitor'
    LAYOUT        = MainWindowLayout()

    def __init__(
            self,
            *args,
            **kwargs
    ):
        if not args and 'title' not in kwargs:
            args = (MainWindow.DEFAULT_TITLE, *args)
        super().__init__(*args, **kwargs)

    def __post_build__(self):
        slider_elem = self.window.find_element('BRIGHTNESS_SLIDER')
        slider_elem.bind(
            '<ButtonRelease-1>',
            lambda event, s=slider_elem: self.window.write_event_value('BRIGHTNESS_SLIDER_DONE', s.get())
        )

    def build_event_handlers(self):
        self.EVENT_COLLECTION.create_event(None, self.stop)

    def handle_event(self, event, *args, **kwargs):
        values = args[0] if args else {}

        if event in (None, 'EXIT_BTTN'):
            self.stop()
            return

        if event == 'BRIGHTNESS_SLIDER':
            brightness(DEVICES[0], int(values.get('BRIGHTNESS_SLIDER', 0)))
            return

        if event == 'BRIGHTNESS_SLIDER_DONE':
            brightness(DEVICES[0], int(values.get('BRIGHTNESS_SLIDER_DONE', 0)))

    def run(self):
        if not self.built:
            raise RuntimeError('Window is not built. Call build() first.')

        if not self.running:
            raise RuntimeError('Window is not running. Call start() first.')

        DEBOUNCE_DELAY = 0.3
        last_change = 0
        pending_value = None

        while self.running:
            event, values = self.window.read(timeout=100)

            if event == 'BRIGHTNESS_SLIDER':
                pending_value = int(values['BRIGHTNESS_SLIDER'])
                last_change = time.time()

            if pending_value is not None and time.time() - last_change > DEBOUNCE_DELAY:
                brightness(DEVICES[0], pending_value)
                pending_value = None

            self.handle_event(event, values)

            if event is None:
                break
