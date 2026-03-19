# IS Matrix Forge - User Manual

## Table of Contents
1. [Introduction](#introduction)
2. [Hardware Setup](#hardware-setup)
3. [Software Installation](#software-installation)
4. [Using the Features](#using-the-features)
5. [Troubleshooting](#troubleshooting)

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
led-matrix-identify
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
You can customize animations by creating or modifying preset files in the `presets`
directory. Each preset is a JSON file that defines animation frames and timing.

To install sample presets:
```bash
is-matrix-forge-install-presets
```

## Troubleshooting

### LED Matrix Not Detected
1. Check the USB connection
2. Verify that the device appears in your system's device list
3. Try a different USB port
4. Restart the application

### Audio Notifications Not Working
1. Ensure your system's audio is working correctly.
2. Verify that the chime library is properly installed.

### Animation Issues
1. Verify that the LED matrix is functioning correctly.
2. Check that the matrix dimensions match the expected 9x34 size.
3. Try clearing the matrix and restarting the application.

### Getting Help
If you encounter issues not covered here, please:
1. Check the GitHub repository for known issues
2. Submit a new issue with detailed information about your problem
3. Include log files and system information in your report
