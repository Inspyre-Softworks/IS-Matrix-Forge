# Getting Started

## What You Need

- Python 3.12 or newer
- A supported 9×34 LED matrix connected over USB
- Hardware identifiers:
  - VID: `0x32AC`
  - PID: `0x20`
  - Serial number prefix: `FRAK`

## Installation

### Option 1: Poetry (recommended for contributors)

```bash
git clone https://github.com/Inspyre-Softworks/IS-Matrix-Forge.git
cd IS-Matrix-Forge
poetry install
poetry shell
```

### Option 2: pip

```bash
git clone https://github.com/Inspyre-Softworks/IS-Matrix-Forge.git
cd IS-Matrix-Forge
pip install .
```

## First Device Check

Use the helper to list discovered devices:

```python
from is_matrix_forge.led_matrix.helpers.device import DEVICES

for dev in DEVICES:
    print(dev)
```

## First Output

Display scrolling text on the first connected device:

```python
from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
from is_matrix_forge.led_matrix.helpers.device import DEVICES

controller = LEDMatrixController(DEVICES[0])
controller.scroll_text("Hello World!", loop=False)
```

## Next Steps

- Read the full [User Manual](user_manual.md)
- Review architecture guidance in [Contributing: Controller Mixins](contributing-mixins.md)
