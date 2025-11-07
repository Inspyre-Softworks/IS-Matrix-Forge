import time
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Optional, Union

from inspy_logger import Loggable
from inspyre_toolbox.syntactic_sweets.classes import validate_type
from serial.tools.list_ports_common import ListPortInfo
from is_matrix_forge.common.helpers import percentage_to_value
from is_matrix_forge.led_matrix.hardware import get_animate, get_brightness, animate, percentage
from is_matrix_forge.led_matrix.controller import LEDMatrixController
from is_matrix_forge.led_matrix.display.animations import goodbye_animation
from is_matrix_forge.led_matrix.helpers.device import check_device
from is_matrix_forge.monitor import (
    DEFAULT_PLUGGED_SOUND,
    DEFAULT_UNPLUGGED_SOUND,
    MOD_LOGGER,
    get_plugged_status,
    PowerMonitorNotRunningError,
    ECH,
)
from is_matrix_forge.notify.sounds import Sound
from is_matrix_forge.monitor.helpers import get_battery_percentage


class PowerMonitor(Loggable):
    '''
    Author: Inspyre Softworks
    Project: IS-Matrix-Forge
    File: monitor.py

    Description:
        Periodically checks AC power status and battery percentage,
        triggers sounds on plug/unplug events, and updates the LED matrix.
        Can run synchronously or in a background thread.

    Properties:
        battery_check_interval (float):
            Seconds to wait between checks.
        controller (LEDMatrixController):
            Active LED matrix controller.
        cycles (int):
            Number of loop iterations since start.
        dev (ListPortInfo):
            The selected serial device (raw port info).
        device (ListPortInfo):
            Alias to dev.
        last_state (Optional[bool]):
            Last known "plugged in" state; None before first check.
        plugged_alert (Sound):
            Sound to play when AC becomes present.
        unplugged_alert (Sound):
            Sound to play when AC is removed.
        plugged_in (bool):
            Current AC status.
        unplugged (bool):
            Convenience negation of plugged_in.
        running (bool):
            Whether the monitor loop is active.
        run_time (float):
            Elapsed time in seconds between start and now/stop.
        start_time/stop_time (Optional[float]):
            Timestamps for last start/stop.
        thread (Optional[Thread]):
            Background thread if running threaded.

    Methods:
        start(threaded: bool = False) -> Optional[Thread]
        stop(without_salutation: bool = False, reason: Optional[str] = None) -> None
        run() -> None
        notify(which: str) -> None
        set_device(device: Union[ListPortInfo, LEDMatrixController]) -> None
    '''

    _running = False
    DEFAULT_CHECK_INTERVAL = 5
    __cycles = 0

    def __init__(
        self,
        device,
        battery_check_interval: int = 5,
        plugged_alert: Optional[Union[str, Path]] = DEFAULT_PLUGGED_SOUND,
        unplugged_alert: Optional[Union[str, Path]] = DEFAULT_UNPLUGGED_SOUND,
    ):
        super().__init__(MOD_LOGGER)
        self.__active_animations = None
        self.__battery_check_interval = None
        self.__dev = None
        self._last_state = None
        self.__plugged_alert = None
        self.__start_time = None
        self.__stop_time = None
        self.__thread = None
        self.__unplugged_alert = None
        self.__controller = None

        self.set_device(device)

        if plugged_alert:
            self.plugged_alert = plugged_alert
        if unplugged_alert:
            self.unplugged_alert = unplugged_alert

        # Initialize the LED matrix brightness to a low value (0-100).
        self.controller.set_brightness(5)
        self.__battery_check_interval = battery_check_interval or self.DEFAULT_CHECK_INTERVAL

    # --- Settings & state ---
    @property
    def active_animations(self)-> Optional[List[Animation]]:
        return self.__active_animations

    @property
    def battery_check_interval(self):
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
        # IMPORTANT: return the stored ListPortInfo, not via controller.
        return self.__dev

    @property
    def device(self):
        return self.dev

    @property
    def last_state(self) -> Optional[bool]:
        '''
        The last observed AC state.

        Returns:
            Optional[bool]: True (plugged), False (unplugged), or None (not checked yet).
        '''
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
        '''
        Whether AC is currently present (does not imply net charging).
        '''
        return get_plugged_status()

    @property
    def running(self):
        return self._running

    @running.setter
    def running(self, new):
        if not self._running and new:
            raise RuntimeError('Cannot start monitor by setting running to True. Use start().')
        if not isinstance(new, bool):
            raise TypeError(f'running must be of type `bool`, not {type(new)}')
        self._running = new

    @property
    def run_time(self):
        if self.__start_time is None:
            raise PowerMonitorNotRunningError("Monitor hasn't been started yet.")
        recent = self.__stop_time if self.__stop_time is not None else time.time()
        return recent - self.__start_time

    @property
    def start_time(self) -> Optional[float]:
        return self.__start_time

    @property
    def stop_time(self) -> Optional[float]:
        return self.__stop_time

    @property
    def thread(self) -> Optional[Thread]:
        if self.__thread is None:
            self.class_logger.error('Either monitor is not running or it is not running in a separate thread.')
        return self.__thread

    @property
    def unplugged(self):
        return not self.plugged_in

    @property
    def unplugged_alert(self) -> 'Sound':
        return self.__unplugged_alert or DEFAULT_UNPLUGGED_SOUND

    @validate_type()
    @unplugged_alert.setter
    def unplugged_alert(self, new):
        if not isinstance(new, Sound):
            raise TypeError(f'unplugged_alert must be of type `Sound`, not {type(new)}')
        self.__unplugged_alert = new

    # --- Behavior ---

    def notify(self, which: str):
        '''
        Send a plug/unplug notification sound, but only when the state changes and
        after at least one status check has occurred.
        '''
        log = self.method_logger
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
        '''
        Main loop; dispatches to event handlers based on AC state and sleeps between checks.
        '''
        from .events import handle_event
        log = self.method_logger
        if not self._running:
            log.error('Monitor is not running')
            raise RuntimeError('Monitor is not running. Use start().')

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
        '''
        Accept either a LEDMatrixController or a ListPortInfo and wire the class up.
        '''
        if isinstance(device, LEDMatrixController):
            self.__controller = device
            self.__dev = device.device
            return
        elif not isinstance(device, ListPortInfo):
            raise TypeError(f'device must be of type `ListPortInfo`, not {type(device)}')

        if not check_device(device):
            raise ValueError(f'device {device} is not available')

        self.__dev = device
        self.__controller = LEDMatrixController(device)

    def start(self, threaded=False):
        '''
        Start the monitor. When threaded, returns the Thread; otherwise blocks.
        '''
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
            self.__thread = t
            ECH.register_handler(self.stop, kwargs={'reason': 'Program exited.'})
            return t
        else:
            try:
                self.run()
            except KeyboardInterrupt:
                log.warning('KeyboardInterrupt received, stopping monitor...')
                self.stop(without_salutation=True, reason='Keyboard interrupt.')

    def stop(self, without_salutation=False, reason=None):
        '''
        Stop the monitor and play a farewell animation unless suppressed.
        '''
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
