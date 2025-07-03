[![PyPI version](https://img.shields.io/pypi/v/IS-Matrix-Forge)](https://pypi.org/project/IS-Matrix-Forge)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/IS-Matrix-Forge)


# IS Matrix Forge

IS Matrix Forge is a toolkit for controlling 9x34 LED matrix displays.  It provides utilities for device discovery, grid manipulation and pattern rendering.  A battery-monitor example demonstrates how to display system power status on a matrix.

## Project Description and Purpose

IS Matrix Forge supplies the core components for driving LED matrices.  The project exposes a flexible API for writing graphics or text to the display and includes helpers for locating connected hardware.  The battery monitor application demonstrates how these pieces fit together to provide real-time system feedback.

Key features:
- Device detection and control
- Grid and pattern utilities
- Animation framework
- Battery-monitor example
- Support for multiple matrices

## Hardware Requirements

- 9x34 LED matrix display
- Serial connection to the computer (USB)
- Supported devices share the following identifiers:
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

### Basic Usage

To start monitoring your battery with default settings:

```python
from is_matrix_forge.monitor import run_power_monitor
from is_matrix_forge.led_matrix.helpers.device import DEVICES

# Get the first available LED matrix device
device = DEVICES[0]

# Start monitoring with default settings
run_power_monitor(device)
```

### Custom Configuration

To customize the monitoring behavior:

```python
from is_matrix_forge.monitor import run_power_monitor
from is_matrix_forge.led_matrix.helpers.device import DEVICES
from pathlib import Path

# Get the first available LED matrix device
device = DEVICES[0]

# Custom sound files
plugged_sound = Path("path/to/custom_plugged_sound.wav")
unplugged_sound = Path("path/to/custom_unplugged_sound.wav")

# Start monitoring with custom settings
run_power_monitor(
    device,
    battery_check_interval=10,  # Check every 10 seconds
    plugged_alert=plugged_sound,
    unplugged_alert=unplugged_sound
)
```

### Running in a Thread

To run the monitor in a background thread:

```python
from is_matrix_forge.monitor import run_power_monitor_threaded
from is_matrix_forge.led_matrix.helpers.device import DEVICES

# Get the first available LED matrix device
device = DEVICES[0]

# Start monitoring in a background thread
monitor = run_power_monitor_threaded(device)
# ``monitor`` is a :class:`threading.Thread` instance
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

Contributions to IS Matrix Forge are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.