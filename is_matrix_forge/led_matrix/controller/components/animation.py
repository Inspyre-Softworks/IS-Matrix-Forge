from __future__ import annotations
from typing import Optional
from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized
from is_matrix_forge.led_matrix.display.animations import flash_matrix


class AnimationManager:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_animation = None

    @synchronized
    def animate(self, enable: bool = True) -> None:
        from is_matrix_forge.led_matrix.hardware import animate
        animate(self.device, enable)

    def play_animation(self, animation):
        from is_matrix_forge.led_matrix.display.animations.animation import Animation
        if not isinstance(animation, Animation):
            raise TypeError(f'Expected Animation; got {type(animation)}')
        self._current_animation = animation
        return animation.play(devices=[self])

    def scroll_text(self, text: str, skip_end_space: bool = False, loop: bool = False):
        from is_matrix_forge.led_matrix.display.text.scroller import TextScroller
        from is_matrix_forge.led_matrix.display.animations.animation import Animation
        from is_matrix_forge.led_matrix.display.assets import fonts as font
        anim = Animation(TextScroller(font).scroll(text, skip_end_space))
        anim.set_all_frame_durations(0.03)
        if loop:
            anim.loop = True
        self._current_animation = anim
        return anim.play(devices=[self])

    @synchronized
    def flash(self, num_flashes: Optional[int] = None, interval: float = 0.33):
        flash_matrix(self, num_flashes=num_flashes, interval=interval)

    @synchronized
    def halt_animation(self) -> None:
        if self.animating:
            self.animate(False)

    @property
    def current_animation(self):
        return self._current_animation

