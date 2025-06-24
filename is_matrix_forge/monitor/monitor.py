
import time
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Optional, Union

from inspy_logger import Loggable
from inspyre_toolbox.syntactic_sweets.classes import validate_type
from serial.tools.list_ports_common import ListPortInfo
from is_matrix_forge.common.helpers import percentage_to_value
from is_matrix_forge.led_matrix import pattern, get_animate, animate, percentage, LEDMatrixController
from is_matrix_forge.led_matrix.display.animations import goodbye_animation
from is_matrix_forge.led_matrix.helpers.device import check_device
from is_matrix_forge.monitor import DEFAULT_PLUGGED_SOUND, DEFAULT_UNPLUGGED_SOUND, MOD_LOGGER, get_plugged_status, \
    PowerMonitorNotRunningError, ECH
from is_matrix_forge.notify.sounds import Sound
from is_matrix_forge.monitor.helpers import get_battery_percentage


class PowerMonitor(Loggable):

    # Properties
    #
    _running         = False
    DEFAULT_CHECK_INTERVAL = 5
    __cycles         = 0

    def __init__(
            self,
            device,
            battery_check_interval: int = 5,
            plugged_alert: Optional[Union[str, Path]] = DEFAULT_PLUGGED_SOUND,
            unplugged_alert: Optional[Union[str, Path]] = DEFAULT_UNPLUGGED_SOUND,

    ):
        super().__init__(MOD_LOGGER)
        self.__battery_check_interval = None
        self.__dev                    = None
        self._last_state             = None
        self.__plugged_alert          = None
        self.__start_time             = None
        self.__stop_time              = None
        self.__thread                 = None
        self.__unplugged_alert        = None
        self.__controller             = None

        self.set_device(device)

        # Set some settings
        # First alerts, if provided
        if plugged_alert:
            self.plugged_alert = plugged_alert

        if unplugged_alert:
            self.unplugged_alert = unplugged_alert

        # Initialize the LED matrix brightness to a low value.
        # The controller API expects a percentage between 0 and 100.
        self.controller.set_brightness(5)
        self.__battery_check_interval = battery_check_interval or self.DEFAULT_CHECK_INTERVAL

    @property
    def battery_check_interval(self):
        """

        Returns:

        """
        return self.__battery_check_interval

    @battery_check_interval.setter
    @validate_type(int, str, float, preferred_type=float, conversion_funcs=[float])
    def battery_check_interval(self, new):

        self.__battery_check_interval = new

    @property
    def controller(self):
        return self.__controller

    @property
    def cycles(self):
        return self.__cycles

    @property
    def dev(self):
        return self.controller.device

    @property
    def device(self):
        return self.dev

    @property
    def last_state(self) -> Optional[bool]:
        """
        The state of the connection to the power supply on last-check.

        Returns:
            Optional[bool]:
                True;
                    The device was plugged into power.
                False;
                    The device was unplugged from power.

                None;
                    The monitor hasn't completed a check yet.
        """
        return self._last_state

    @property
    def plugged_alert(self) -> Sound:
        return self.__plugged_alert or DEFAULT_PLUGGED_SOUND

    @validate_type(Sound)
    @plugged_alert.setter
    def plugged_alert(self, new):
        if not isinstance(new, Sound):
            raise TypeError(f'plugged_alert must be of type `Sound`, not {type(new)}')

        self.__plugged_alert = new

    @property
    def plugged_in(self):
        """
        Whether the device is currently plugged into power.

        Returns:
            bool:
                True;
                    The device is currently plugged into power. This is not an indicator (necessarily) that;
                        - The battery level is increasing
                        - The battery level is not decreasing
                        - The battery is gaining a net-positive charge level

                    This is an indicator that;
                        - A power supply is connected to the device

                False;
                    The device is currently unplugged from power.
        """
        return get_plugged_status()

    @property
    def running(self):
        """
        Whether the power-monitor is running.

        Returns:
            bool:
                True;
                    The monitor is running.

                False;
                    The monitor is not running.
        """
        return self._running

    @running.setter
    def running(self, new):
        """
        The setter for the `running` property. You can only set `running` to `False`, this will stop the monitor.

        Parameters:
            new:
                The new value for `running`.

        Returns:
            None

        Raises:
            RuntimeError:
                If you try to set `running` to `True`

            TypeError:
                If `new` is not of type `bool`
        """
        if not self._running and new:
            raise RuntimeError('Cannot start monitor by setting running to `True`. Use the `start` method instead.')

        if not isinstance(new, bool):
            raise TypeError(f'running must be of type `bool`, not {type(new)}')

        self._running = new

    @property
    def run_time(self):
        """
        The time the monitor has been running. This is the time since the monitor was started, or the time between
        starting and stopping the monitor if it has been stopped.

        Returns:
            float:
                The run time in seconds.
        """
        if not hasattr(self, 'start_time'):
            raise PowerMonitorNotRunningError('Monitor hasn\'t even been started yet!')

        recent = self.stop_time if hasattr(self, 'stop_time') else time.time()
        return recent - self.start_time

    @property
    def start_time(self) -> Optional[float]:
        return self.__start_time

    @property
    def stop_time(self) -> Optional[float]:
        """
        (**Read-only property**)

        The time the monitor was last stopped.

        Returns:
            Optional[float]:
                The time the monitor was last stopped.

                `None`;
                    The monitor hasn't been stopped yet

        """
        return self.__stop_time

    @property
    def thread(self) -> Optional[Thread]:
        """
        The thread object that is running the monitor loop. If the monitor is not running in a separate thread, this
        property will return `None`.

        Returns:
            Optional[Thread]:
                The thread that is running the monitor loop; if the monitor is running in a separate thread.
                None otherwise
        """
        if self.__thread is None:
            self.class_logger.error('Either monitor is not running or it is not running in a separate thread.')

        return self.__thread

    @property
    def unplugged(self):
        """
        Whether the laptop is currently unplugged from AC power.

        Returns:
            bool:
                True;
                    The device is currently unplugged from power, and the battery is discharging.

                False;
                    The device is currently plugged into power. This is not an indicator (necessarily) that;
                        - The battery level is increasing
                        - The battery level is not decreasing
                        - The battery is gaining a net-positive charge level
        """
        return not self.plugged_in

    @property
    def unplugged_alert(self) -> 'Sound':
        """
        The sound to play when the device is unplugged from power.

        Returns:
            Sound:
                The sound to play when the device is unplugged from power.
        """
        if not self.__unplugged_alert:
            return DEFAULT_UNPLUGGED_SOUND

        return self.__unplugged_alert

    @validate_type()
    @unplugged_alert.setter
    def unplugged_alert(self, new):
        """
        The setter for the `unplugged_alert` property. This must be of type `Sound`.

        Parameters:
            new:


        Returns:

        """
        if not isinstance(new, Sound):
            raise TypeError(f'unplugged_alert must be of type `Sound`, not {type(new)}')

        self.__unplugged_alert = new

    def notify(self, which: str):
        """
        Notify the user of a power event (plugged, unplugged).

        Parameters:
            which (str):
                The type of notification to send ('plugged' or 'unplugged').
        """
        log = self.method_logger
        # Just return if the first check hasn't been completed yet.

        if self.last_state is None:
            log.debug('Status: Not yet checked')
            return

        if which.lower() == 'plugged':
            log.debug('Status: Plugged in')
            if not self.last_state:
                log.debug(f'Using {self.plugged_alert} to notify user...')
                self.plugged_alert.notify()
        elif which.lower() == 'unplugged':
            log.debug('Status: Unplugged')
            if self.last_state:
                log.debug(f'Using {self.unplugged_alert} to notify user...')
                self.unplugged_alert.notify()

    def run(self):
        """
        Run the power monitor. This is where the main loop of the monitor is located. It (roughly) does the following
        while playing notification sounds when the power supply is plugged in or unplugged:
          1. Check the battery level.
          2. If the power supply is unplugged, display the battery level on the LED matrix.
          3. If the power supply is plugged in, animate the LED matrix.
          4. Repeat.

        Note:
            This method is called by the `start` method and should not be called directly.
        """
        from .events import handle_event
        log = self.method_logger
        if not self._running:
            log.error('Monitor is not running')
            raise RuntimeError('Monitor is not running. If you want to start it, use the `start` method.')

        log.debug('Running monitor...')

        while self.running:
            
            state = 'plugged' if self.plugged_in else 'unplugged'
            handle_event(state, self)

            if not self.running:
                self.controller.clear()
                break

            self.__cycles += 1

            sleep(self.battery_check_interval)

    def set_device(self, device):

        if isinstance(device, LEDMatrixController):
            self.__controller = device
            device = self.controller.device
        elif not isinstance(device, ListPortInfo):
            raise TypeError(f'device must be of type `ListPortInfo`, not {type(device)}')

        if not check_device(device):
            raise ValueError(f'device {device} is not available')

        self.__dev = device
        self.__controller = LEDMatrixController(self.dev)

    def start(self, threaded=False):
        """
        Start the power monitor.

        Parameters:
            threaded (bool):
                If True, run the monitor in a separate thread.

        Returns:
            Optional[Thread]:
                The thread that is running the monitor loop; if `threaded` is True.
                None otherwise.

        """
        log = self.method_logger
        log.debug('Starting monitor')

        if self.running:
            log.warning('Monitor is already running')
            raise RuntimeError('Monitor is already running')

        self._running = True
        log.debug('Set running to True')
        self.__start_time = time.time()

        if threaded:
            t = Thread(target=self.run, daemon=True)
            t.start()
            ECH.register_handler(self.stop, kwargs={'reason': 'Program exited.'})

        try:
            self.run()
        except KeyboardInterrupt:
            log.warning('KeyboardInterrupt received, stopping monitor...')
            self.stop(without_salutation=True, reason='Keyboard interrupt.')

    def stop(self, without_salutation=False, reason=None):
        """
        Stop the power monitor.

        Parameters:
            without_salutation (bool):
                If True, skip the goodbye animation that plays by default on the LED matrix.
        """

        log = self.method_logger

        if not self.running:
            log.error('Monitor is not running')
            raise PowerMonitorNotRunningError("Can't call stop() on a monitor that is not running")
        else:
            log.debug('Stopping monitor...')
        self.__stop_time = time.time()
        self.running = False
        log.debug('"running" flag set to False...waiting for thread to finish')

        if reason:
            log.info(f'Stopping monitor due to: {reason}')
        else:
            log.info('Stopping monitor. With no reason.')

        if not without_salutation:
            goodbye_animation(self.dev)
        else:
            log.debug('Skipping goodbye salutation...')

        if get_animate(self.dev):
            animate(self.dev, False)

        log.debug('Clearing LED matrix...')
        self.controller.clear()
