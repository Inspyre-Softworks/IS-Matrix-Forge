"""LED matrix controller façade."""

from __future__ import annotations

from typing import Any, Optional

from .animations import AnimationService
from .brightness import BrightnessService
from .context import BreatherPauseCtx
from .device import DeviceRef
from .grid import GridService
from .identity import IdentifyService
from .keep_alive import KeepAliveService
from .patterns import PatternService
from .threading import ThreadSafetyMixin


class LEDMatrixController(ThreadSafetyMixin):
    """Thin façade delegating LED matrix operations to services."""

    def __init__(
        self,
        device: Any,
        default_brightness: Optional[int] = None,
        skip_init_brightness_set: Optional[bool] = False,
        skip_init_clear: Optional[bool] = False,
        init_grid: Optional[Any] = None,
        do_not_show_grid_on_init: Optional[bool] = False,
        thread_safe: Optional[bool] = False,
        do_not_warn_on_thread_misuse: Optional[bool] = False,
        hold_all: Optional[bool] = False,
        skip_greeting: Optional[bool] = False,
        skip_identify: Optional[bool] = False,
        skip_all_init_animations: Optional[bool] = False,
    ) -> None:
        super()._thread_safe_setup(
            thread_safe=thread_safe, warn_on_thread_misuse=not do_not_warn_on_thread_misuse
        )

        self.breathing = False

        self.device_ref = DeviceRef(device)
        self.brightness_service = BrightnessService(default_brightness)
        self.grid_service = GridService(init_grid=init_grid)
        self.pattern_service = PatternService()
        self.animation_service = AnimationService(self)
        self.identify_service = IdentifyService(self.device_ref)
        self.keep_alive_service = KeepAliveService()

        if not skip_init_clear:
            self.grid_service.clear_matrix()

        if not skip_init_brightness_set:
            self.brightness_service.set_brightness(self.brightness_service.brightness)

        if not skip_identify and not skip_all_init_animations:
            self.identify_service.identify()

        if not skip_greeting and not skip_all_init_animations:
            self.identify_service.greet()

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------
    def breather_paused(self) -> BreatherPauseCtx:
        """Return a context manager that pauses the breather effect."""

        return BreatherPauseCtx(self)

    # ------------------------------------------------------------------
    # Device identity delegation
    # ------------------------------------------------------------------
    @property
    def device(self) -> Any:
        return self.device_ref.device

    @property
    def location(self) -> Any:
        return self.device_ref.location

    @property
    def location_abbrev(self) -> Any:
        return self.device_ref.location_abbrev

    @property
    def side_of_keyboard(self) -> Any:
        return self.device_ref.side_of_keyboard

    @property
    def slot(self) -> Any:
        return self.device_ref.slot

    @property
    def name(self) -> Any:
        return self.device_ref.name

    @property
    def serial_number(self) -> Any:
        return self.device_ref.serial_number

    # ------------------------------------------------------------------
    # Keep‑alive delegation
    # ------------------------------------------------------------------
    @property
    def keep_alive(self) -> bool:
        return self.keep_alive_service.enabled

    @keep_alive.setter
    def keep_alive(self, value: bool) -> None:
        self.keep_alive_service.enabled = bool(value)

    # ------------------------------------------------------------------
    # Brightness delegation
    # ------------------------------------------------------------------
    @property
    def brightness(self) -> int:
        return self.brightness_service.brightness

    def set_brightness(self, value: int) -> int:
        return self.brightness_service.set_brightness(value)

    # ------------------------------------------------------------------
    # Grid delegation
    # ------------------------------------------------------------------
    def clear_matrix(self) -> None:
        self.grid_service.clear_matrix()

    def draw_grid(self, grid: Optional[Any] = None) -> None:
        self.grid_service.draw_grid(grid)

    def show_text(self, text: str) -> None:
        self.grid_service.show_text(text)

    def draw_percentage(self, percent: int) -> None:
        self.grid_service.draw_percentage(percent)

    # ------------------------------------------------------------------
    # Pattern delegation
    # ------------------------------------------------------------------
    def draw_pattern(self, name: str) -> None:
        self.pattern_service.draw_pattern(name, self.grid_service)

    def list_patterns(self) -> list[str]:
        return self.pattern_service.list_patterns()

    @property
    def built_in_pattern_names(self) -> list[str]:
        return self.pattern_service.built_in_pattern_names

    # ------------------------------------------------------------------
    # Animation delegation
    # ------------------------------------------------------------------
    def animate(self, func, *args, **kwargs):
        return self.animation_service.animate(func, *args, **kwargs)

    @property
    def animating(self) -> bool:
        return self.animation_service.animating

    def halt_animation(self) -> None:
        self.animation_service.halt_animation()

    def play_animation(self, animation) -> Any:
        return self.animation_service.play_animation(animation)

    def scroll_text(self, text: str) -> Any:
        return self.animation_service.scroll_text(text)

    def flash(self, color: Any) -> Any:
        return self.animation_service.flash(color)

    # ------------------------------------------------------------------
    # Identity delegation
    # ------------------------------------------------------------------
    def identify(self) -> Any:
        return self.identify_service.identify()

    @property
    def display_name(self) -> Any:
        return self.identify_service.display_name

    @property
    def display_location(self) -> Any:
        return self.identify_service.display_location

