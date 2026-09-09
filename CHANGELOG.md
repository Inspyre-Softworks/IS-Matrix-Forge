# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Per-LED grayscale brightness control through `BrightnessManager`, including
  complete percentage/raw framebuffer writes and safe single-pixel updates.
- Atomic low-level framebuffer transactions using the Framework LED Matrix
  `StageGreyCol` and `DrawGreyColBuffer` commands.
- Host-side framebuffer state tracking, binary-grid synchronization, and
  fail-closed partial updates when the current framebuffer is unknown.
- Grayscale framebuffer snapshots in display history and grayscale restoration.
- `AnimationManager.animations_dir`, `animation_names`,
  `list_animation_names()`, and `load_animation()` for discovering and loading
  JSON animations by name from the application animation directory.
- `Animation.list_names()` and `Animation.from_name()` for the same named-file
  workflow without constructing a controller.
- Regression tests for serial packet layout, validation, partial-write safety,
  per-pixel preservation, and animation storage discovery.
- Controller docs: Architecture/MRO summary added to `README.md`.
- ADR 0001: Controller MRO and cooperative initialization (`docs/adr/0001-controller-mro-and-cooperative-init.md`).
- Contributing guide for authoring mixins (`docs/contributing-mixins.md`).
- Example mixin template (`is_matrix_forge/led_matrix/controller/components/example_template.py`).
- Tests: MRO order verification (`tests/test_controller_mro.py`).
- Tests: Identify parameter validation (`tests/test_identify_validation.py`).
- `scroll-text` CLI: New `-f`/`--frame-duration` argument (float, default `0.33`) to control how long each animation frame is displayed.
- Tests: `--frame-duration` CLI argument parsing and `frame_duration` forwarding to `controller.scroll_text()`.

### Changed
- Package version advanced to `1.0.0-dev.31`.
- Binary drawing operations now synchronize the known per-LED framebuffer;
  firmware-rendered patterns, percentages, and text invalidate it.
- Grayscale column compatibility helpers now share the validated low-level
  framebuffer transport.
- Reorganized code from `is_matrix_forge.inputmodule.ledmatrix` into multiple specialized modules:
  - `is_matrix_forge.led_matrix.hardware`: Low-level hardware communication functions
  - `is_matrix_forge.led_matrix.display.patterns`: Pattern-related display functions
  - `is_matrix_forge.led_matrix.display.text`: Text and symbol rendering functions
  - `is_matrix_forge.led_matrix.display.media`: Image and video-related functions
- Moved all display-related functionality to the `is_matrix_forge.led_matrix.display` package
- Updated all imports throughout the codebase to use the new module structure
- Improved code organization with better separation of concerns
- LEDMatrixController: Adopted cooperative `super()` initialization across all mixins and
  finalized MRO to ensure safe access during `__init__`:
  `DeviceBase → KeepAliveManager → AnimationManager → DrawingManager → BrightnessManager → BreatherManager → IdentifyManager → Loggable`.
- LEDMatrixController: Standardized constructor to pass `parent_log_device=` through the cooperative chain
  (compatible with InspyLogger and the fallback Loggable stub).
- BrightnessManager: Participates in cooperative initialization and initializes internal
  brightness state before `super()`, then applies the initial brightness after downstream
  mixins (e.g., BreatherManager) are initialized.
- Helpers: Controller creation now attempts `default_brightness` and falls back if unsupported
  by a custom controller class (compatibility with legacy controllers).
- Grid: Improved flat glyph shape inference; no longer assumes width=5 by default. Uses
  factor-pair heuristic bounded by target canvas, preferring common widths.
- DeviceBase: Initializes `_device`, thread-safety flags, and lock before forwarding kwargs
  via `super()` so mixins can safely access `self.device` during init.
- `AnimationManager.scroll_text()`: Default `frame_duration` changed from `0.05` → `0.33` s.
- `TextScrollerConfig`: Default `frame_duration` changed from `0.05` → `0.33` s.
- `scroll_text_command`: `frame_duration` is now forwarded to `controller.scroll_text()` in both the direct and span-animation paths.
- `Animation`: Logger child name corrected to avoid duplicating the program-name prefix; removed stray `LOGGER.info('Test')` call; added structured `debug`/`error` log calls during `__init__`.

### Removed
- Dependency on the monolithic `ledmatrix.py` module

### Benefits
- Better code organization with logical separation of functionality
- Improved maintainability through smaller, focused modules
- Clearer API with functions grouped by purpose
- Easier to extend with new features in the future

### Fixed
- Identify: Validates `duration` and `cycles` to prevent division-by-zero and invalid intervals.
- Initialization robustness: Cooperative MRO chain and tests reduce risk of ordering regressions.
 - Controller init ordering bugs causing `AttributeError` during threaded creation:
   - Ensure `parent_log_device` propagates through MRO to InspyLogger’s `Loggable`.
   - Initialize `DeviceBase` state before cooperative `super()`.
   - Initialize `BrightnessManager` fields before `super()` and apply brightness after.
