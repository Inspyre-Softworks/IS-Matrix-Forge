# IS Matrix Forge - User Manual

## Table of Contents
1. Introduction
2. Hardware Setup
3. Software Installation
4. Using the Features
5. Per-LED Brightness
6. Stored Animations
7. Troubleshooting

## Introduction

IS Matrix Forge is a Python framework for creating applications that drive
9×34 LED matrix displays. It provides high-level helpers for talking to the
hardware, tools for building animations, and utilities such as progress bars.

## Hardware Setup

### Required Components
- LED Matrix display compatible with this software (VID: 0x32AC, PID: 0x20, SN prefix: FRAK)
- USB cable for connecting the LED Matrix to your computer
- Computer with available USB port

### Connection Steps
1. Connect the LED Matrix to your computer using the USB cable.
2. Verify that the LED Matrix is recognized by your operating system:
   - On Windows: Check Device Manager under "Ports (COM & LPT)"
   - On macOS: Open Terminal and run `ls /dev/tty.*`
   - On Linux: Open Terminal and run `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`

## Software Installation

### System Requirements
- Python 3.12 or higher

### Using Poetry (Recommended)

```bash
git clone https://github.com/Inspyre-Softworks/IS-Matrix-Forge.git
cd IS-Matrix-Forge
poetry install
poetry shell
```

### Using pip

```bash
git clone https://github.com/Inspyre-Softworks/IS-Matrix-Forge.git
cd IS-Matrix-Forge
pip install .
```

### Verifying Installation
To verify installation, run the identify command:
```bash
led-matrix identify-matrices
```

This command detects connected LED matrices and displays identification information on each one.

## Using the Features

### Identify Connected Devices

```python
from is_matrix_forge.led_matrix.helpers.device import DEVICES

for dev in DEVICES:
    print(dev)
```

### Display Text on the Matrix

```python
from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
from is_matrix_forge.led_matrix.helpers.device import DEVICES

ctrl = LEDMatrixController(DEVICES[0])
ctrl.scroll_text("Hello World!", loop=False)
```

### Progress Bars

```python
import time
from is_matrix_forge.progress import tqdm

for _ in tqdm(range(100)):
    time.sleep(0.05)
```

### Customizing Animations
Grid presets remain in the configured `presets` directory. Named animation
files live separately in the controller's platform-specific
`animations_dir`. Each animation is a JSON array defining frames and timing.

To install sample presets:
```bash
led-matrix install-presets
```

## Per-LED Brightness

Framework LED Matrix modules support an independent 8-bit grayscale value for
each of their 306 LEDs. IS Matrix Forge provides percentage and native raw APIs:

```python
levels = [[0 for _ in range(34)] for _ in range(9)]
levels[0][0] = 20
levels[4][17] = 50
levels[8][33] = 100

ctrl.set_brightness_grid(levels)
ctrl.set_pixel_brightness(4, 17, 75)

raw_levels = ctrl.pixel_brightness_grid
print(ctrl.get_pixel_brightness_raw(4, 17))
```

`set_brightness_grid()` and `set_pixel_brightness()` accept percentages from
`0..100`. `set_brightness_grid_raw()` and `set_pixel_brightness_raw()` accept
integers from `0..255`.

The firmware stages nine complete columns and commits them together. Because
stock firmware does not provide a framebuffer-read command, a single-pixel
update is allowed only when this controller process knows the complete current
framebuffer. Complete grayscale writes establish that state; binary
`draw_grid()` calls synchronize it as `0/255`. Firmware-rendered patterns,
percentages, and text invalidate it. Attempting a partial update while state is
unknown raises `FramebufferStateUnknownError` instead of clearing neighboring
LEDs.

## Stored Animations

`AnimationManager` creates and uses a platform-specific animation directory:

```python
print(ctrl.animations_dir)
print(ctrl.animation_names)

animation = ctrl.load_animation("status-pulse")
ctrl.play_animation(animation)
```

`list_animation_names()` returns sorted JSON file stems. `load_animation()`
accepts a stem or a `.json` filename, searches only the configured animation
directory, and returns an `Animation` without playing it. Pass
`animations_dir=...` to `LEDMatrixController` to override the default location.

The `Animation` class exposes the same behavior without a controller:

```python
from is_matrix_forge.led_matrix.display.animations import Animation

print(Animation.list_names())
animation = Animation.from_name("status-pulse")
```

## Troubleshooting

### LED Matrix Not Detected
1. Check the USB connection
2. Verify that the device appears in your system's device list
3. Try a different USB port
4. Restart the application

### Animation Issues
1. Verify that the LED matrix is functioning correctly.
2. Check that the matrix dimensions match the expected 9x34 size.
3. Try clearing the matrix and restarting the application.
4. Confirm named files appear in `ctrl.list_animation_names()`.

### Partial Brightness Update Rejected

Call `set_brightness_grid()` or `set_brightness_grid_raw()` once to establish a
known complete framebuffer, then retry the single-pixel update.

### Getting Help
If you encounter issues not covered here, please:
1. Check the GitHub repository for known issues
2. Submit a new issue with detailed information about your problem
3. Include log files and system information in your report
