from time import sleep

from is_matrix_forge.led_matrix.hardware import brightness
from is_matrix_forge.led_matrix.display.text import show_string
from .audio_visualizer import AudioVisualizer


def clear(dev):
    brightness(dev, 0)


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
    'goodbye_animation',
]
