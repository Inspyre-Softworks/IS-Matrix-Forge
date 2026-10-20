from collections.abc import Callable
from types import MappingProxyType
from time import sleep

from is_matrix_forge.led_matrix.hardware import brightness
from .animation import Animation
from .frame import Frame
from .audio_visualizer import AudioVisualizer


def clear(dev):
    brightness(getattr(dev, 'device', dev), 0)


def flash_matrix(dev, num_flashes=6, interval=.33, min_brightness=None, max_brightness=None):
    initial_brightness = dev.brightness
    max_brightness = max_brightness or initial_brightness
    min_brightness = min_brightness or 0

    for _ in range(num_flashes):
        dev.brightness = min_brightness
        sleep(interval)

        dev.brightness = max_brightness
        sleep(interval)

    dev.brightness = initial_brightness



def checkerboard_cycle(dev):
    from is_matrix_forge.led_matrix.display.patterns.built_in.stencils import checkerboard
    frame = 2

    while frame < 5:
        hardware_device = getattr(dev, 'device', dev)
        brightness(hardware_device, 25)
        print(f'Processing frame: {frame}')
        sleep(1)
        checkerboard(hardware_device, frame)
        frame += 1


def goodbye_animation(dev):
    clear(dev)
    sleep(.1)
    checkerboard_cycle(dev)
    sleep(.5)
    from is_matrix_forge.led_matrix.display.text import show_string

    show_string(getattr(dev, 'device', dev), 'Bye')


_BUILTIN_ANIMATIONS: dict[str, Callable[..., None]] = {
    'checkerboard_cycle': checkerboard_cycle,
    'flash': flash_matrix,
    'goodbye': goodbye_animation,
}
BUILTIN_ANIMATIONS = MappingProxyType(_BUILTIN_ANIMATIONS)


def _normalize_animation_name(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError('animation name must be a string')
    return name.strip().lower().replace('-', '_').replace(' ', '_')


def available_animations() -> tuple[str, ...]:
    """Return the canonical names of animations bundled with the package."""
    return tuple(sorted(BUILTIN_ANIMATIONS))


def get_builtin_animation(name: str) -> Callable[..., None]:
    """Resolve a bundled animation by its short, normalized name."""
    normalized = _normalize_animation_name(name)
    try:
        return BUILTIN_ANIMATIONS[normalized]
    except KeyError as exc:
        choices = ', '.join(available_animations())
        raise ValueError(f'Unknown built-in animation {name!r}. Available: {choices}') from exc


def run_builtin_animation(dev, name: str, **options) -> None:
    """Run a bundled animation against a device or controller."""
    get_builtin_animation(name)(dev, **options)


__all__ = [
    'AudioVisualizer',
    'Animation',
    'BUILTIN_ANIMATIONS',
    'Frame',
    'available_animations',
    'clear',
    'checkerboard_cycle',
    'flash_matrix',
    'get_builtin_animation',
    'goodbye_animation',
    'run_builtin_animation',
]
