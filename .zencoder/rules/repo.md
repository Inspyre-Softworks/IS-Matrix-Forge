---
description: Repository Information Overview
alwaysApply: true
---

# IS Matrix Forge Information

## Summary
IS Matrix Forge is a Python framework for creating applications that drive 9×34 LED matrix displays. It provides high-level helpers for communicating with the hardware, tools for building animations, and utilities such as progress bars and a battery monitor.

## Structure
- **is_matrix_forge/**: Main package containing all core functionality
  - **led_matrix/**: LED matrix control and display components
  - **monitor/**: Battery monitoring functionality
  - **notify/**: Notification system
  - **designer_gui/**: GUI for designing matrix displays
  - **serial_com/**: Serial communication with hardware
- **tests/**: Unit tests for the project
- **presets/**: Predefined matrix patterns and animations
- **docs/**: Documentation including ADRs and user manual
- **.github/**: CI/CD workflows for building and publishing

## Language & Runtime
**Language**: Python
**Version**: 3.12+
**Build System**: Poetry
**Package Manager**: Poetry

## Dependencies
**Main Dependencies**:
- pyserial (>=3.5,<4.0) - Serial communication with LED matrix
- chime (>=0.7.0,<0.8.0) - Audio notifications
- inspy-logger (>=3.2.3,<4.0.0) - Logging system
- inspyre-toolbox (>=1.6.0) - Utility functions
- pillow (>=11.2.1,<12.0.0) - Image processing
- opencv-python (>=4.11.0.86,<5.0.0.0) - Image processing
- pysimplegui-4-foss (>=4.60.4.1) - GUI components
- psutil (6.1.1) - System monitoring for battery status

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
**Run Command**:
```bash
# Build and run with Docker Compose
docker-compose up --build
```

## Testing
**Framework**: pytest
**Test Location**: tests/
**Naming Convention**: test_*.py files with test_* functions
**Configuration**: pyproject.toml [tool.pytest.ini_options]
**Run Command**:
```bash
poetry run pytest
```

## Main Entry Points
**Scripts**:
- led-matrix-identify: Identify connected LED matrices
- install-presets: Install predefined matrix patterns
- pixel-grid: Display pixel grid utility

**Core Components**:
- LEDMatrixController: Main controller for LED matrix operations
- Grid: Class for creating and manipulating matrix displays
- Battery Monitor: System for monitoring and displaying battery status