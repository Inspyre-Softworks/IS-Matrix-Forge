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
    Loggable,
    DeviceBase,
    KeepAliveManager,
    AnimationManager,
    DrawingManager,
    BrightnessManager,
    BreatherManager,
    IdentifyManager,
):
    ...
```

Rationale for ordering:
- DeviceBase must initialize early so `self.device` exists for downstream mixins.
- BrightnessManager before BreatherManager because Breather reads controller
  brightness during its initialization.
- BreatherManager before IdentifyManager because `IdentifyManager.__init__` may
  call `@synchronized` methods which rely on a breather pause context.

The controller’s `__init__` uses a single cooperative `super().__init__` call,
passing common kwargs (`device`, `thread_safe`, and logging handle). To support
both InspyLogger and the lightweight fallback, we attempt `parent_log_device=`
first and map to `logger=` if needed.

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
- Controller helpers now catch `TypeError` for `default_brightness` to preserve
  backward compatibility with legacy controllers.

