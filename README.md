[![PyPI version](https://img.shields.io/pypi/v/IS-Matrix-Forge)](https://pypi.org/project/IS-Matrix-Forge)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/IS-Matrix-Forge)


# IS Matrix Forge

**IS Matrix Forge** is a Python framework for creating applications that drive
9×34 LED matrix displays.  It provides high level helpers for talking to the
hardware, tools for building animations, and utilities such as progress bars and
a battery monitor.

## Project Overview

Matrix Forge grew out of the LED Matrix Battery Monitor project.  The goal is to
make it easy to create rich LED matrix experiences from Python.  In addition to
monitoring the battery, you can design custom frames, display scrolling text,
run animations, and integrate the LED matrix with your own applications.

Highlighted features include:
- Device discovery and control via `pyserial`
- Drawing grids and patterns with the `Grid` class
- Built-in and custom animations
- Progress bars that render on the matrix
- A battery monitor example using these building blocks

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
- pysimplegui-4-foss (>=4.60.4.1,<5.0.0.0) - GUI components
- tk (>=0.1.0,<0.2.0) - GUI toolkit
- easy-exit-calls (>=1.0.0.dev1,<2.0.0) - Exit handling
- psutil - For battery status monitoring

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

### Progress Bars

```python
import time
from is_matrix_forge.progress import tqdm

for _ in tqdm(range(100)):
    time.sleep(0.05)
```

### Battery Monitor Example

```python
from is_matrix_forge.monitor import run_power_monitor
from is_matrix_forge.led_matrix.helpers.device import DEVICES

device = DEVICES[0]
run_power_monitor(device)
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

### Battery Status Not Updating

1. Make sure psutil is properly installed.
2. Check that your system supports battery status monitoring through psutil.
3. Try increasing the battery_check_interval to reduce CPU usage.

### Animation Issues

1. Verify that the LED matrix is functioning correctly.
2. Check that the matrix dimensions match the expected 9x34 size.
3. Try clearing the matrix and restarting the application.

## Contributing

Contributions are welcome! If you have ideas or improvements for Matrix Forge,
feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.
