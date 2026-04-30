[![PyPI version](https://img.shields.io/pypi/v/IS-Matrix-Forge)](https://pypi.org/project/IS-Matrix-Forge)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/IS-Matrix-Forge)


# IS Matrix Forge

**IS Matrix Forge** is a Python framework for creating applications that drive
9×34 LED matrix displays.  It provides high level helpers for talking to the
hardware, tools for building animations, and utilities such as progress bars.

## Project Overview

Matrix Forge grew out of the LED Matrix project.  The goal is to
make it easy to create rich LED matrix experiences from Python.  You can design
custom frames, display scrolling text, run animations, and integrate the LED
matrix with your own applications.

Highlighted features include:
- Device discovery and control via `pyserial`
- Drawing grids and patterns with the `Grid` class
- Built-in and custom animations
- Progress bars that render on the matrix

## What It Tracks and Where Data Comes From

IS Matrix Forge focuses on **local hardware and UI inputs** that drive the LED
matrix, not on ingesting external telemetry streams.

**Primary inputs and events**
- **LED matrix commands** such as grids, patterns, text, animations, and
  brightness changes. The controller can record these display events to support
  history and restore operations.【F:is_matrix_forge/led_matrix/controller/components/history/manager.py†L13-L199】
- **Local UI events** from the included PySimpleGUI tools (designer) for
  controlling what the matrix displays.【F:is_matrix_forge/designer_gui/main_window/__init__.py†L165-L272】

## How “Real-Time” Updates Work

The real-time behavior is **local polling and rendering**: the controller reacts
to commands and display events, immediately updating the matrix.

## Scope and Use Cases

Matrix Forge is designed for **device UI, hardware status, and visual
notifications**, such as:
- LED matrix dashboards for a workstation or appliance
- Custom animations, text banners, or progress indicators

It is **not** a SOC/observability platform and does **not** ingest or correlate
network logs, SIEM feeds, or remote sensor telemetry out of the box. Its inputs
are primarily local hardware state and user-driven UI events.

## Hardware Requirements

- LED Matrix display with dimensions 9x34 (compatible with the project's specifications)
- Serial connection to the computer (USB)
- The LED matrix should have the following hardware identifiers:
  - VID: 0x32AC
  - PID: 0x20
  - Serial Number Prefix: FRAK

## Software Dependencies

This project requires Python 3.12 or newer and the following dependencies:

- chime (>=0.7.0,<0.8.0) - For audio notifications
- pyserial (>=3.5,<4.0) - For serial communication with the LED matrix
- inspy-logger (>=3.2.3,<4.0.0) - For logging
- inspyre-toolbox (>=1.6.0) - Utility functions
- pillow (>=11.2.1,<12.0.0) - Image processing
- opencv-python (>=4.11.0.86,<5.0.0.0) - Image processing

## Installation Instructions

### Using Poetry (Recommended)

1. Clone the repository:
   ```
   git clone https://github.com/Inspyre-Softworks/IS-Matrix-Forge.git
   cd IS-Matrix-Forge
   ```

2. Install dependencies using Poetry:
   ```
   poetry install
   ```

3. Activate the virtual environment:
   ```
   poetry shell
   ```

### Using pip

1. Clone the repository:
   ```
   git clone https://github.com/Inspyre-Softworks/IS-Matrix-Forge.git
   cd IS-Matrix-Forge
   ```

2. Install the package:
   ```
   pip install .
   ```

## Usage Examples

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

### Navigate an Animation

```python
from is_matrix_forge.led_matrix.display.animations.animation import Animation
from is_matrix_forge.led_matrix.display.animations.frame.base import Frame

animation = Animation(
    frame_data=[
        Frame(grid=[[1]], duration=0.1, width=1, height=1),
        Frame(grid=[[0]], duration=0.1, width=1, height=1),
        Frame(grid=[[1]], duration=0.1, width=1, height=1),
    ]
)

animation.fast_forward()   # jump all the way to the last frame
animation.rewind()         # jump all the way back to the first frame
animation.fast_forward(2)  # move ahead two frames from the current cursor
animation.rewind(1)        # move back one frame from the current cursor
animation.seek(0)          # jump to an absolute frame index
```

`Animation.rewind()` and `Animation.fast_forward()` use relative step counts.
Passing `0` or omitting the argument jumps to the beginning/end respectively.
Use `Animation.seek(index)` when you want to jump to an absolute frame index.

## Controller Architecture

- Composition is implemented via multiple mixins that all use cooperative
  initialization with `super()`.
- MRO ordering ensures safe access patterns during `__init__`:
  - `DeviceBase` initializes early so mixins can use `self.device`.
  - `BrightnessManager` precedes `BreatherManager` because the breather inspects
    brightness at init time.
  - `BreatherManager` precedes `IdentifyManager` because `IdentifyManager` may
    call `@synchronized` methods in `__init__` that rely on a breather pause context.
  - `Loggable` is placed last so the cooperative chain can pass `logger=` safely.
- Thread safety: pass `thread_safe=True` to enable an internal `RLock` used by
  the `@synchronized` decorator for device operations.
- Logging: integrates with InspyLogger when available and falls back to a simple
  logger; the controller passes `parent_log_device` through the cooperative chain
  and the fallback stub supports it.

MRO diagram (left → right, init order)
`DeviceBase → KeepAliveManager → AnimationManager → DrawingManager → BrightnessManager → BreatherManager → IdentifyManager → Loggable`

### Progress Bars

```python
import time
from is_matrix_forge.progress import tqdm

for _ in tqdm(range(100)):
    time.sleep(0.05)
```

## Troubleshooting

### LED Matrix Not Detected

1. Check that the LED matrix is properly connected to your computer.
2. Verify that the LED matrix has the correct hardware identifiers (VID, PID, SN_PREFIX).
3. Make sure you have the necessary permissions to access the serial port.
4. Try running the application with administrator/root privileges.

### Audio Notifications Not Working

1. Ensure your system's audio is working correctly.
2. Check that the WAV files for notifications exist in the expected locations.
3. Verify that the chime library is properly installed.

### Animation Issues

1. Verify that the LED matrix is functioning correctly.
2. Check that the matrix dimensions match the expected 9x34 size.
3. Try clearing the matrix and restarting the application.

## Contributing

Contributions are welcome! If you have ideas or improvements for Matrix Forge,
feel free to open an issue or submit a pull request.

- See docs/contributing-mixins.md for guidance on authoring new controller mixins
  using cooperative initialization and the `@synchronized` decorator.
  A minimal reference mixin is available at
  `is_matrix_forge/led_matrix/controller/components/example_template.py`.

Quick checklist for a new controller mixin
- Create `is_matrix_forge/led_matrix/controller/components/<name>.py` with `ClassNameManager`.
- In `__init__(...)`, accept keyword-only args and call `super().__init__(**kwargs)`.
- Avoid IO-heavy work in `__init__`; use `@synchronized` for device methods.
- If calling synchronized methods in `__init__`, ensure MRO places you after `BreatherManager`.
- If adding to the main controller, place after `DeviceBase` and before `IdentifyManager`; consider dependencies.
- Provide docstrings, type hints, and a small usage example or test.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.
