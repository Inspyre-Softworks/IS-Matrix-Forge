# ADR 0001: Controller MRO and Cooperative Initialization

Date: 2025-08-27

## Status

Accepted

## Context

The LED matrix controller composes several concerns (device IO, drawing,
animations, brightness, keep-alive, identify, breather) via multiple
inheritance. Without care, multiple inheritance can introduce subtle issues
around initialization order, attribute availability (`self.device`), and
decorators that assume certain components (e.g., a breather pause context).

## Decision

We adopt cooperative initialization using `super().__init__(**kwargs)` across
all mixins, and we enforce an explicit MRO that satisfies component
dependencies during `__init__`:

```
class LEDMatrixController(
    DeviceBase,
    DisplayHistoryManager,
    KeepAliveManager,
    GameManager,
    AnimationManager,
    DrawingManager,
    BrightnessManager,
    BreatherManager,
    IdentifyManager,
    Loggable,
):
    ...
```

Rationale for ordering:
- DeviceBase must initialize early so `self.device` exists for downstream mixins.
- DisplayHistoryManager wraps later display and brightness methods so successful
  grayscale frame commits can be recorded and restored.
- GameManager initializes before display managers so synchronized operations can
  reject display changes while a device game is running.
- BrightnessManager before BreatherManager because Breather reads controller
  brightness during its initialization.
- BreatherManager before IdentifyManager because `IdentifyManager.__init__` may
  call `@synchronized` methods which rely on a breather pause context.
- Loggable is placed last so we can pass `logger=` through the cooperative
  chain without colliding with other mixin kwargs.

The controller’s `__init__` uses a single cooperative `super().__init__` call,
passing common kwargs (`device`, `thread_safe`, and logging handle).
We pass `parent_log_device=` through the chain; the fallback `Loggable` stub
accepts this parameter as well.

## Consequences

- Mixins must call `super().__init__(**kwargs)` to keep the chain intact.
- The helpers creating controllers pass `default_brightness` but include a
  compatibility fallback for controllers that don’t accept it.
- The `@synchronized` decorator expects either `self.breather.paused` or
  `self.breather_paused()` to exist. BreatherManager ensures this is true during
  early initialization.

## Alternatives Considered

- Explicitly calling each base `__init__` in sequence: more brittle and error
  prone; harder to maintain when signatures evolve.
- Flattening responsibilities into a single class: reduces flexibility and test
  surface; makes features harder to mix and match or reuse.

## Implementation Notes

- BrightnessManager was updated to participate in cooperative `super()` init.
- BrightnessManager owns host-side per-LED framebuffer state because stock
  firmware cannot read the currently displayed grayscale framebuffer.
- AnimationManager accepts an optional `animations_dir` and otherwise provisions
  the platform-specific application animation directory.
- Controller helpers now catch `TypeError` for `default_brightness` to preserve
  backward compatibility with legacy controllers.
