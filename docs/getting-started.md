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

## Per-LED Brightness

Set a complete 9×34 percentage grid before making partial updates:

```python
levels = [[0 for _ in range(34)] for _ in range(9)]
levels[4][17] = 25

controller.set_brightness_grid(levels)
controller.set_pixel_brightness(4, 17, 75)
```

The grid is column-major (`levels[x][y]`). Percentage methods accept `0..100`;
their `*_raw` counterparts accept the hardware's native `0..255` levels.

## Stored Animations

Place animation JSON files in `controller.animations_dir`, then discover and
load them without hard-coding paths:

```python
print(controller.list_animation_names())
animation = controller.load_animation("status-pulse")
controller.play_animation(animation)
```

For standalone use, call `Animation.list_names()` and
`Animation.from_name("status-pulse")`.

## Next Steps

- Read the full [User Manual](user_manual.md)
- Review architecture guidance in [Contributing: Controller Mixins](contributing-mixins.md)
