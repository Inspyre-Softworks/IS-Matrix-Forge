# IS Matrix Forge Information

## Summary
IS Matrix Forge is a Python framework for creating applications that drive 9×34 LED matrix displays. It provides high-level helpers for communicating with LED matrix hardware, tools for building animations, and utilities such as progress bars and a battery monitor. The framework enables developers to create rich LED matrix experiences from Python.

## Structure
- **is_matrix_forge/**: Main package containing all framework components
  - **assets/**: Audio and font resources
  - **common/**: Common utilities and helpers
  - **designer_gui/**: GUI for designing LED matrix patterns
  - **led_matrix/**: Core LED matrix functionality
  - **monitor/**: Battery monitoring functionality
  - **notify/**: Notification system
  - **serial_com/**: Serial communication with hardware
  - **inputmodule/**: Input handling modules
- **presets/**: JSON configuration files for predefined patterns
- **tests/**: Test files for the framework
- **docs/**: Documentation files

## Language & Runtime
**Language**: Python
**Version**: 3.12+
**Build System**: Poetry
**Package Manager**: Poetry (with pip fallback)

## Dependencies
**Main Dependencies**:
- pyserial (>=3.5,<4.0) - Serial communication
- inspy-logger (>=3.2.3,<4.0.0) - Logging
- inspyre-toolbox (>=1.6.0) - Utility functions
- pillow (>=11.2.1,<12.0.0) - Image processing
- opencv-python (>=4.11.0.86,<5.0.0.0) - Image processing
- pysimplegui-4-foss (==4.60.4.1) - GUI components
- chime (>=0.7.0,<0.8.0) - Audio notifications
- easy-exit-calls (>=1.0.0.dev1,<2.0.0) - Exit handling

**Development Dependencies**:
- ipython (^9.1.0)
- prompt-toolkit (^3.0.51)
- ptipython (^1.0.1)
- ipyboost (1.0.0.a3)

## Build & Installation
```bash
# Using Poetry (recommended)
git clone https://github.com/Inspyre-Softworks/IS-Matrix-Forge.git
cd IS-Matrix-Forge
poetry install
poetry shell

# Using pip
git clone https://github.com/Inspyre-Softworks/IS-Matrix-Forge.git
cd IS-Matrix-Forge
pip install .
```

## Docker
**Dockerfile**: Dockerfile
**Base Image**: python:3.12-slim
**Configuration**: Multi-stage build with separate builder and final stages
**Build Command**:
```bash
docker build -t is-matrix-forge .
```
**Run Command**:
```bash
docker compose up
```

## Testing
**Framework**: pytest
**Test Location**: tests/
**Configuration**: pyproject.toml
**Run Command**:
```bash
pytest
```

## Main Components

### LED Matrix Controller
The core component for interacting with LED matrix hardware:
```python
from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
from is_matrix_forge.led_matrix.helpers.device import DEVICES

ctrl = LEDMatrixController(DEVICES[0])
ctrl.scroll_text("Hello World!", loop=False)
```

### Grid System
Provides a grid-based interface for drawing patterns:
```python
from is_matrix_forge.led_matrix.led_matrix import Grid

grid = Grid()
grid.set_pixel(x, y, True)  # Turn on a pixel
```

### Progress Bar
Displays progress on the LED matrix:
```python
from is_matrix_forge.progress import tqdm

for _ in tqdm(range(100)):
    time.sleep(0.05)
```

### Battery Monitor
Monitors and displays battery status:
```python
from is_matrix_forge.monitor import run_power_monitor
from is_matrix_forge.led_matrix.helpers.device import DEVICES

device = DEVICES[0]
run_power_monitor(device)
```

### Designer GUI
A graphical interface for designing LED matrix patterns and animations.

### Serial Communication
Handles low-level communication with the LED matrix hardware via serial connection.