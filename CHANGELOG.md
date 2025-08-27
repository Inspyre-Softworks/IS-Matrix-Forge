# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Controller docs: Architecture/MRO summary added to `README.md`.
- ADR 0001: Controller MRO and cooperative initialization (`docs/adr/0001-controller-mro-and-cooperative-init.md`).
- Contributing guide for authoring mixins (`docs/contributing-mixins.md`).
- Example mixin template (`is_matrix_forge/led_matrix/controller/components/example_template.py`).
- Tests: MRO order verification (`tests/test_controller_mro.py`).
- Tests: Identify parameter validation (`tests/test_identify_validation.py`).

### Changed
- Reorganized code from `led_matrix_battery.inputmodule.ledmatrix` into multiple specialized modules:
  - `led_matrix_battery.led_matrix.hardware`: Low-level hardware communication functions
  - `led_matrix_battery.led_matrix.display.patterns`: Pattern-related display functions
  - `led_matrix_battery.led_matrix.display.text`: Text and symbol rendering functions
  - `led_matrix_battery.led_matrix.display.media`: Image and video-related functions
- Moved all display-related functionality to the `led_matrix_battery.led_matrix.display` package
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
