from time import sleep

from is_matrix_forge.led_matrix.hardware import brightness
from .animation import Animation
from .frame import Frame
from .audio_visualizer import AudioVisualizer


def clear(dev):
    brightness(dev, 0)


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
        brightness(dev, 25)
        print(f'Processing frame: {frame}')
        sleep(1)
        checkerboard(dev, frame)
        frame += 1


def goodbye_animation(dev):
    clear(dev)
    sleep(.1)
    checkerboard_cycle(dev)
    sleep(.5)
    show_string(dev, 'Bye')


__all__ = [
    'AudioVisualizer',
    'clear',
    'checkerboard_cycle',
    'flash_matrix',
    'goodbye_animation',
]
