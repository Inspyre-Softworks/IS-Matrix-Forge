from __future__ import annotations

from typing import Optional, Dict, Any

from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized
from is_matrix_forge.led_matrix.display.animations import flash_matrix
from is_matrix_forge.led_matrix.display.animations import Animation
from is_matrix_forge.led_matrix.display.animations.text_scroller import (
    TextScroller,
    TextScrollerConfig,
)
from is_matrix_forge.assets.font_map.base import FontMap


class AnimationManager:
    """
    AnimationManager

    Description:
        Mixin/manager for playing animations on a matrix device, including
        text scrolling via the TextScroller pipeline (adapter + trimming aware).

    Properties:
        device:
            The underlying hardware controller (provided by the concrete class).

        current_animation:
            The most recently played Animation (if any).

    Methods:
        animate(enable):
            Enable/disable device-side animation mode.

        play_animation(animation):
            Validate and play a provided Animation (thread-safe).

        scroll_text(...):
            Build and play a scrolling text Animation with rich configuration.
            All exposed parameters are honored and forwarded to the scroller.

        flash(num_flashes, interval):
            Flash the matrix.

        halt_animation():
            Stop the hardware animation mode if active.
    """

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._current_animation: Optional[Animation] = None

    # --- Hardware animation toggle -------------------------------------------------

    @synchronized
    def animate(self, enable: bool = True) -> None:
        """
        Enable or disable device-side animation mode.

        Parameters:
            enable:
                True to enable, False to disable.
        """
        # Local import avoids hard import dependency for non-matrix test contexts
        from is_matrix_forge.led_matrix.hardware import animate as hw_animate
        hw_animate(self.device, enable)

    # --- Animation playback --------------------------------------------------------

    @synchronized
    def play_animation(self, animation: Animation) -> None:
        """
        Validate and play a provided Animation.

        Parameters:
            animation:
                An Animation instance to play on this device.

        Raises:
            TypeError:
                If 'animation' is not an Animation.
        """
        if not isinstance(animation, Animation):
            raise TypeError(f'Expected Animation; got {type(animation)}')
        self._current_animation = animation
        animation.play(devices=[self])

    # --- Text scrolling ------------------------------------------------------------

    def _build_font_map_subset(self, text: str, font_map: Optional[FontMap]) -> Dict[str, Any]:
        """
        Build a glyph dictionary for the characters present in 'text'.

        Notes:
            - Uses provided FontMap or a default FontMap().
            - Falls back to a 1x1 empty glyph for missing characters.

        Returns:
            dict mapping uppercase character -> glyph data structure expected by TextScroller.
        """
        fm = font_map or FontMap()
        glyphs: Dict[str, Any] = {}
        for ch in set(text.upper()):
            try:
                glyphs[ch] = fm.lookup(ch, kind=None)
            except Exception:
                # Graceful fallback so we never crash on unknown chars
                glyphs[ch] = [[0]]
        return glyphs

    def scroll_text(
            self,
            text: str,
            *,
            spacing: int = 1,
            frame_duration: float = 0.05,
            wrap: bool = False,
            direction: str = 'horizontal',
            font_map: Optional[FontMap] = None,
            loop: bool = False,
            set_duration_override: Optional[float] = None,
    ) -> Animation:
        """
        Build and play a scrolling text Animation using the current TextScrollerConfig API.
        """
        # Build a minimal dict for the characters used
        fm = font_map or FontMap()
        fm_dict = {}
        for ch in set(text.upper()):
            try:
                fm_dict[ch] = fm.lookup(ch, kind=None)
            except Exception:
                fm_dict[ch] = [[0]]

        cfg = TextScrollerConfig(
            text=text,
            font_map=fm_dict,
            spacing=spacing,
            frame_duration=frame_duration,
            wrap=wrap,
            direction=direction,
        )

        scroller = TextScroller(cfg)
        anim = scroller.generate_animation()

        if set_duration_override is not None:
            anim.set_all_frame_durations(set_duration_override)

        anim.loop = bool(loop)
        self._current_animation = anim

        # IMPORTANT: play using this controller so frames reuse the existing device connection
        anim.play(devices=[self])
        return anim

    # --- Utilities ----------------------------------------------------------------

    @synchronized
    def flash(self, num_flashes: Optional[int] = None, interval: float = 0.33) -> None:
        """
        Flash the matrix on/off.

        Parameters:
            num_flashes:
                Number of flashes; None means continuous until externally stopped.
            interval:
                Seconds between on/off toggles.
        """
        flash_matrix(self, num_flashes=num_flashes, interval=interval)

    @synchronized
    def halt_animation(self) -> None:
        """
        Stop device-side animation mode if active.
        """
        if getattr(self, 'animating', False):
            self.animate(False)

    # --- Accessors ----------------------------------------------------------------

    @property
    def current_animation(self) -> Optional[Animation]:
        """The most recently played Animation (if any)."""
        return self._current_animation
