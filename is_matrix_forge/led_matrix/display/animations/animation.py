import logging
import threading
from threading import Event
from typing import List, Dict, Optional, Union, Any
from time import sleep  # Potentially used by Frame.play()
import time
from pathlib import Path
from contextlib import contextmanager  # <-- NEW

from serial.tools.list_ports_common import ListPortInfo
from is_matrix_forge.log_engine import ROOT_LOGGER, Loggable
from is_matrix_forge.led_matrix.display.animations.frame.base import Frame
from is_matrix_forge.led_matrix.helpers import get_json_from_file
from is_matrix_forge.led_matrix.display.animations.errors import AnimationFinishedError


LOGGER = ROOT_LOGGER.get_child('led_matrix.display.animations.animation')


class Animation(Loggable):
    """
    Represents a sequence of Frames with playback controls.
    """

    # Class-level registry of all currently playing animations.
    __currently_playing: List['Animation'] = []
    __currently_playing_lock = threading.Lock()  # <-- NEW: protect registry

    def __init__(
            self,
            frame_data: Optional[List[Dict[str, Any]]] = None,
            fallback_frame_duration: float = 0.33,
            loop: bool = False,
            thread_safe: bool = False,
            breathe_on_pause: bool = False,
            devices: Optional[List[ListPortInfo]] = None
    ):
        """
        Initialize a new Animation instance.

        Parameters:
            frame_data: list of dict or Frame to seed the animation.
            fallback_frame_duration: default duration for frames.
            loop: whether to loop at end.
            thread_safe: run in a separate thread if True.
            breathe_on_pause: breathe effect when paused.
            devices: list of ListPortInfo LED devices.
        """
        super().__init__(parent_log_device=LOGGER)
        log = self.class_logger

        # 1) set all attributes to defaults
        self._stop_event = Event()
        self.__lock = None
        self.__thread_lock = None
        self.__pause_event = None
        self.__breathing_thread = None
        self.__making_thread_safe = False
        self.__breathe_on_pause = False
        self.__thread_safe = False
        self.__cursor = 0
        self.__playing = False
        self.__frames: List[Frame] = []
        self.__devices: List[ListPortInfo] = []
        self.__loop = False

        # 2) configure devices & threading
        self._configure_devices(devices, thread_safe, breathe_on_pause)
        log.debug('Devices configured: %s (thread_safe=%s)', devices, thread_safe)

        # 3) apply high-level settings
        self.fallback_frame_duration = fallback_frame_duration
        log.debug('fallback_frame_duration set to %s', fallback_frame_duration)
        self.loop = loop
        log.debug('loop set to %s', loop)

        # 4) load any provided frames
        if frame_data:
            self._load_frames(frame_data)
            log.debug('Loaded %d frame(s) from frame_data', len(self.__frames))
        elif frame_data is not None:
            log.error('frame_data was provided but no frames were loaded')

        if self.frames and len(self.frames) >= 1:
            log.debug(f'Loaded {len(self.frames)} frames')
        else:
            log.debug('No frames loaded.')
            if frame_data:
                log.error(f'Provided frame data: {frame_data} but no frames loaded!')

        # 5) reset cursor into valid range
        self._reset_cursor()

        self.breathe_on_pause = breathe_on_pause

    # -------------------------------------------------------------------------
    # Class-level animation management
    # -------------------------------------------------------------------------

    @classmethod
    def currently_playing(cls) -> tuple['Animation', ...]:
        """
        Return a snapshot of all animations currently marked as playing.

        Returns:
            tuple[Animation, ...]:
                A tuple of currently playing animations.
        """
        with cls.__currently_playing_lock:
            return tuple(cls.__currently_playing)

    @classmethod
    def stop_all(cls, *, do_not_clear: bool = False) -> None:
        """
        Stop all currently playing animations.

        Parameters:
            do_not_clear (bool):
                If True, do not clear devices when stopping each animation.
        """
        with cls.__currently_playing_lock:
            # Copy so we don't mutate while iterating
            running = list(cls.__currently_playing)

        for ani in running:
            ani.stop(do_not_clear=do_not_clear)

    @classmethod
    @contextmanager
    def managed(cls, animation: 'Animation', *, do_not_clear: bool = False):
        """
        Context manager to track an animation's lifetime.

        Ensures that, when the context exits (normally or via exception),
        the animation is stopped and removed from the registry.

        Usage:
            ani = Animation.from_file('foo.json')

            with Animation.managed(ani):
                ani.play(devices)

        Parameters:
            animation (Animation):
                The animation to manage.
            do_not_clear (bool):
                If True, do not clear devices when stopping on exit.
        """
        try:
            yield animation
        finally:
            # This is idempotent: if play() already finished and set
            # is_playing False, stop() will just ensure _stop_event is set
            # and clear devices (unless do_not_clear is True).
            animation.stop(do_not_clear=do_not_clear)

    @contextmanager
    def running(self, *, do_not_clear: bool = False):
        """
        Instance-level convenience context manager.

        Equivalent to:
            with Animation.managed(self, do_not_clear=...): ...

        Usage:
            ani = Animation.from_file('foo.json')

            with ani.running():
                ani.play(devices)
        """
        try:
            yield self
        finally:
            self.stop(do_not_clear=do_not_clear)

    # -------------------------------------------------------------------------
    # Existing methods unchanged below, except for is_playing setter
    # -------------------------------------------------------------------------

    def _configure_devices(
            self,
            devices: Optional[List[ListPortInfo]],
            thread_safe: bool,
            breathe_on_pause: bool
    ) -> None:
        """
        Assign devices list, and if requested, make this animation thread-safe.
        """
        if devices:
            self.devices = devices

        if thread_safe:
            # note: property setter for breathe_on_pause handles validation
            self.breathe_on_pause = breathe_on_pause
            self.make_thread_safe()

    def _load_frames(self, frame_data: List[Union[Dict[str, Any], Frame]]) -> None:
        """
        Normalize incoming frame_data (dicts or Frame instances) into self.__frames.
        """
        # detect if they already handed us Frame objects
        first = frame_data[0]
        if isinstance(first, Frame):
            # print('received list of frames')
            self.__frames = list(frame_data)  # shallow copy
            return

        # otherwise expect a list of dicts
        for f_dict in frame_data:
            frame_obj = Frame.from_dict(f_dict)

            # if they left duration at DEFAULT, apply our fallback
            if frame_obj.duration == Frame.DEFAULT_DURATION:
                frame_obj.duration = self.fallback_frame_duration

            self.__frames.append(frame_obj)

    def _reset_cursor(self) -> None:
        """Ensure cursor is valid (zero if no frames, else within range)."""
        if not self.__frames:
            self.__cursor = 0
        else:
            self.__cursor %= len(self.__frames)

    @property
    def breathe_on_pause(self) -> bool:
        """Get whether the animation breathes on pause."""
        return self.__breathe_on_pause

    @breathe_on_pause.setter
    def breathe_on_pause(self, new_value: bool) -> None:
        if not isinstance(new_value, bool):
            raise TypeError('Breathe on pause must be a boolean value.')
        self.__breathe_on_pause = new_value

    @property
    def cursor(self) -> int:
        """Get the current position (index) in the animation sequence."""
        return self.__cursor

    @cursor.setter
    def cursor(self, new_value: int) -> None:
        """
        Set the current position in the animation sequence.
        """
        if not isinstance(new_value, int):
            raise TypeError('Cursor must be an integer.')

        if not self.__frames:
            if new_value == 0:
                self.__cursor = 0  # Allow setting to 0 if no frames
                return
            raise ValueError('Cannot set cursor on an animation with no frames.')

        if not (0 <= new_value < len(self.__frames)):
            raise IndexError(f'Cursor out of bounds. Must be between 0 and {len(self.__frames) - 1}.')

        self.__cursor = new_value

    @property
    def cursor_at_end(self) -> bool:
        """Get whether the cursor is at the end of the animation sequence."""
        return self.__cursor == len(self.__frames) - 1

    @property
    def playback_finished(self) -> bool:
        """Return whether playback has advanced past the final frame."""
        return bool(self.__frames) and self.__cursor >= len(self.__frames)

    @property
    def devices(self) -> List[Any]:
        """Get the list of devices used by the animation."""
        return self.__devices

    @devices.setter
    def devices(self, value: Union[Any, List[Any]]):
        """
        Set the devices used by the animation.
        """
        self.__devices = value if isinstance(value, list) else [value]

    @property
    def fallback_frame_duration(self) -> float:
        """Get the default duration for frames that don't specify one."""
        return self.__fallback_frame_duration

    @fallback_frame_duration.setter
    def fallback_frame_duration(self, new_value: Union[float, int]) -> None:
        if not isinstance(new_value, (float, int)):
            raise TypeError('Fallback frame duration must be a float or integer.')
        if new_value < 0:
            raise ValueError('Fallback frame duration must be non-negative.')
        self.__fallback_frame_duration = float(new_value)

    @property
    def frames(self) -> List[Frame]:
        """Get the list of frames that make up the animation."""
        return self.__frames

    @property
    def loop(self) -> bool:
        """Get whether the animation should loop when it reaches the end."""
        return self.__loop

    @loop.setter
    def loop(self, new_value: bool) -> None:
        if not isinstance(new_value, bool):
            raise TypeError('Loop must be a boolean value.')
        self.__loop = new_value

    @property
    def is_empty(self) -> bool:
        """Check if the animation has any frames."""
        return not self.__frames

    @property
    def is_playing(self) -> bool:
        """Check if the animation is currently playing."""
        return self.__playing

    @is_playing.setter
    def is_playing(self, new: bool) -> None:
        """
        Set the playing state of the animation.
        """
        if not isinstance(new, bool):
            raise TypeError('Playing state must be a boolean value.')

        cls = type(self)

        with cls.__currently_playing_lock:
            if new:
                if self not in cls.__currently_playing:
                    cls.__currently_playing.append(self)
            else:
                if self in cls.__currently_playing:
                    cls.__currently_playing.remove(self)

        self.__playing = new

    @property
    def is_thread_safe(self) -> bool:
        """Check if the animation is thread-safe."""
        return self.__thread_safe

    @is_thread_safe.setter
    def is_thread_safe(self, new: bool) -> None:
        if not isinstance(new, bool):
            raise TypeError('Thread safety must be a boolean value.')

        if new and not self.__thread_safe and not self.__making_thread_safe:
            self.make_thread_safe()

        self.__thread_safe = new

    @property
    def thread_lock(self):
        if not self.is_thread_safe:
            raise RuntimeError('Thread lock is not available in non-thread-safe mode.')

        return self.__thread_lock

    def __check_ready(self) -> bool:
        if self.is_empty:
            raise ValueError('Cannot play an animation with no frames.')

        if not self.__cursor:
            self.__cursor = 0

    def __clear_screen(self, devices: Optional[List] = None):
        devices = devices if devices is not None else self.devices

        for dev in devices:
            dev.clear()

    def __normalize_devices(self, devices):
        from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController

        if devices is None:
            if self.devices is None:
                raise ValueError('You need to provide a device!')
            else:
                devices = self.devices

        if not isinstance(devices, list):
            devices = [devices]

        normalized = []

        for device in devices:
            if isinstance(device, LEDMatrixController):
                normalized.append(device)
            elif isinstance(device, ListPortInfo):
                normalized.append(LEDMatrixController(device))
            else:
                raise TypeError('Devices must be either LEDMatrixController or ListPortInfo objects.')

        return normalized

    def make_thread_safe(self, breathe_on_pause: bool = False) -> None:
        if not self.is_thread_safe:
            self.__making_thread_safe = True
            self.__thread_lock = threading.Lock()
            self.__pause_event = threading.Event()
            self.__breathe_on_pause = breathe_on_pause
            self.is_thread_safe = True

    def pause(self, keep_frame_displayed: bool = True) -> None:
        """Pauses animation playback and keeps the current frame displayed."""
        if not self.is_thread_safe:
            raise RuntimeError('pause() requires thread-safe mode to be enabled.')

        with self.thread_lock:
            self.__playing = False
            self.__pause_event.clear()

            if keep_frame_displayed and not self.__breathing_thread:
                self.__breathing_thread = threading.Thread(
                    target=self._paused_display_loop,
                    daemon=True
                )
                self.__breathing_thread.start()

    def play(self, devices: Optional[List['LEDMatrixController']] = None, skip_clear_screen: bool = False) -> None:
        """
        Play the animation on the LED matrix.
        """
        if self.playback_finished:
            raise AnimationFinishedError('Try rewinding the animation first.')

        self.__check_ready()
        devices = self.__normalize_devices(devices)

        if devices:
            self.devices = devices

        self._stop_event.clear()
        self.is_playing = True
        try:
            while self.is_playing and not self._stop_event.is_set():
                for i in range(self.__cursor, len(self.__frames)):
                    if self._stop_event.is_set():
                        break

                    self.play_frame(
                        i,
                        devices,
                        stop_event=self._stop_event,
                    )

                if self._stop_event.is_set():
                    break

                if self.__loop:
                    self.rewind()
                else:
                    self.is_playing = False

                if not skip_clear_screen:
                    self.__clear_screen(devices)

        except KeyboardInterrupt:
            LOGGER.info('Animation playback interrupted by user input.')
            self.stop()

    def play_frame(
        self,
        index: int,
        devices,
        *,
        stop_event: Event | None = None,
        advance_cursor: bool = True,
    ) -> None:
        frame = self.__frames[index]

        for device in devices:
            frame.play(device, stop_event)

        if advance_cursor:
            self.__cursor = index + 1

    def resume(self) -> None:
        """Resumes playback from paused state."""
        if not self.is_thread_safe:
            raise RuntimeError('resume() requires thread-safe mode to be enabled.')

        with self.thread_lock:
            self._stop_event.clear()
            self.__playing = True
            self.__pause_event.set()

        if self.__breathing_thread and self.__breathing_thread.is_alive():
            self.__breathing_thread.join(timeout=0.1)
            self.__breathing_thread = None

    def seek(self, index: int) -> None:
        """
        Jump to an absolute frame index.

        Parameters:
            index (int):
                Zero-based frame index to move to.
        """
        if not isinstance(index, int):
            raise TypeError('"index" must be an integer!')

        if self.is_empty:
            if index != 0:
                raise ValueError('Frame out of range')
        elif index not in range(len(self.frames)):
            raise ValueError('Frame out of range')

        self._stop_event.clear()
        self.cursor = index

    def rewind(self, steps: int = 0) -> None:
        """
        Move the cursor backward by ``steps`` frames.

        Parameters:
            steps (int):
                Number of frames to move backward. When omitted or set to ``0``,
                rewind all the way to the first frame. Positive values are
                clamped at the first frame.
        """
        if not isinstance(steps, int):
            raise TypeError('"steps" must be an integer!')
        if steps < 0:
            raise ValueError('"steps" must be non-negative!')

        if self.is_empty:
            if steps != 0:
                raise ValueError('Cannot rewind an animation with no frames.')
            self._stop_event.clear()
            self.cursor = 0
            return

        if steps == 0:
            self.seek(0)
            return

        current = len(self.frames) if self.playback_finished else self.cursor
        target = max(0, current - steps)
        self.seek(target)

    def fast_forward(self, steps: int = 0) -> None:
        """
        Move the cursor forward by ``steps`` frames.

        Parameters:
            steps (int):
                Number of frames to move forward. When omitted or set to ``0``,
                fast-forward all the way to the last frame. Positive values are
                clamped at the last frame.
        """
        if not isinstance(steps, int):
            raise TypeError('"steps" must be an integer!')
        if steps < 0:
            raise ValueError('"steps" must be non-negative!')

        if self.is_empty:
            if steps != 0:
                raise ValueError('Cannot fast-forward an animation with no frames.')
            self._stop_event.clear()
            self.cursor = 0
            return

        if steps == 0:
            self.seek(len(self.frames) - 1)
            return

        if self.playback_finished:
            target = len(self.frames) - 1
        else:
            target = min(len(self.frames) - 1, self.cursor + steps)

        self.seek(target)

    def stop(self, do_not_clear=False) -> None:
        self._stop_event.set()
        self.is_playing = False
        if not do_not_clear:
            for device in self.devices:
                device.clear()

    def _advance_cursor(self, step: int) -> bool:
        """
        Internal helper to advance or rewind the cursor.
        """
        if self.is_empty:
            return False

        new_cursor = self.__cursor + step

        if 0 <= new_cursor < len(self.__frames):
            self.__cursor = new_cursor
            return True
        elif self.__loop:
            if new_cursor >= len(self.__frames):
                self.__cursor = 0
            else:
                self.__cursor = len(self.__frames) - 1
            return True
        else:
            return False

    def _paused_display_loop(self):
        """Keeps redrawing the current frame while paused. Adds breathing effect if enabled."""
        breath_phase = 0.0
        while not self.__pause_event.is_set():
            current_frame = self.__frames[self.cursor]
            for device in self.devices:
                current_frame.play(device)
                if self.breathe_on_pause:
                    brightness = 0.5 + 0.5 * abs((time.time() % 2) - 1)
                    device.set_brightness(brightness)
            sleep(1)

    def next_frame(self, device: Any = None) -> None:
        """
        Advance to and play the next frame. Wraps if looping.
        """
        if self.is_empty:
            raise ValueError('Cannot play next frame: animation is empty.')
        if self._advance_cursor(1):
            self.__frames[self.__cursor].play(device)

    def previous_frame(self, device: Any = None) -> None:
        """
        Move to and play the previous frame. Wraps if looping.
        """
        if self.is_empty:
            raise ValueError('Cannot play previous frame: animation is empty.')
        if self._advance_cursor(-1):
            self.__frames[self.__cursor].play(device)

    def set_all_frame_durations(self, duration: Union[float, int]) -> None:
        """
        Set the duration for all frames in the animation.
        """
        if not isinstance(duration, (float, int)):
            raise TypeError('Duration must be a float or integer.')
        if duration < 0:
            raise ValueError('Duration must be non-negative.')

        if self.is_empty:
            raise ValueError('Cannot set frame durations: animation is empty.')

        for frame in self.__frames:
            frame.duration = float(duration)

    def set_frame_duration(self, frame_index: int, duration: Union[float, int]) -> None:
        """
        Set the duration for a specific frame in the animation.
        """
        if not isinstance(duration, (float, int)):
            raise TypeError('Duration must be a float or integer.')
        if duration < 0:
            raise ValueError('Duration must be non-negative.')

        if 0 <= frame_index < len(self.__frames):
            self.__frames[frame_index].duration = float(duration)
        else:
            raise IndexError(f'Frame index {frame_index} out of bounds (0-{len(self.__frames) - 1}).')

    @classmethod
    def from_file(
            cls,
            filename: Union[str, Path],
            fallback_frame_duration: float = 0.33,
            loop: bool = False
    ) -> 'Animation':
        """
        Create an Animation instance from a JSON file.
        """
        raw_data = get_json_from_file(filename)

        if not isinstance(raw_data, list):
            raise ValueError(f'File {filename!r} does not contain a valid JSON array of frames.')

        processed_frame_data: List[Dict[str, Any]] = []
        for i, item in enumerate(raw_data):
            if isinstance(item, dict) and 'grid' in item:
                processed_frame_data.append(item)
            elif isinstance(item, list):
                if not all(isinstance(row, list) for row in item):
                    raise ValueError(
                        f'Invalid raw grid data at index {i} in file {filename!r}. Expected list of lists.'
                    )
                processed_frame_data.append({
                    'grid': item,
                    'duration': fallback_frame_duration
                })
            else:
                raise ValueError(
                    f'Invalid frame data type at index {i} in file {filename!r}. Expected dict or list (grid).'
                )

        return cls(
            frame_data=processed_frame_data,
            fallback_frame_duration=fallback_frame_duration,
            loop=loop
        )

    def __len__(self) -> int:
        """Return the number of frames in the animation."""
        return len(self.__frames)
