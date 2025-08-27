# Contributing: Controller Mixins

This project composes controller behavior with multiple mixins. To keep
initialization safe and predictable, all mixins must follow a few rules.

## Cooperative Initialization

- Always call `super().__init__(**kwargs)` in your mixin’s `__init__`.
- Accept only keyword arguments and forward unknown kwargs via `**kwargs`.
- Do not call other base class `__init__` methods directly.

Example:

```python
class FooManager:
    def __init__(self, *, foo_enabled: bool = True, **kwargs):
        super().__init__(**kwargs)
        self._foo_enabled = bool(foo_enabled)
```

## Side Effects During `__init__`

- Assume `DeviceBase` is initialized before your mixin, but avoid heavy
  side-effects in `__init__` (network/IO) unless strictly necessary.
- If you must access the device in `__init__`, ensure your mixin appears after
  `DeviceBase` in the controller’s bases.

## `@synchronized` Decorator

- Methods that interact with hardware should use
  `is_matrix_forge.led_matrix.controller.helpers.threading.synchronized`.
- If your mixin’s `__init__` invokes a synchronized method, ensure the breather
  context is already available (i.e., your mixin appears after
  `BreatherManager` in the MRO). Prefer deferring such calls until after init.

## Logging

- Use `self.method_logger` for method-level logs and `self.class_logger` for
  broader context. The controller injects a logger compatible with
  InspyLogger when available, falling back to the standard library.

## Parameters and Defaults

- Prefer explicit keyword-only parameters; keep defaults conservative.
- If a parameter is optional for some controllers, accept it and ignore it if
  not applicable—this improves compatibility with helpers.

## Tests

- Add targeted tests for any complex logic in your mixin.
- Avoid leaking threads: if you start background threads, provide a clean stop
  path and guard against joining from the same thread.

## Common Pitfalls

- Forgetting `super().__init__(**kwargs)` breaks the init chain.
- Doing IO-heavy work in `__init__` can slow down controller creation and cause
  ordering hazards.
- Accessing `self.breather` or synchronized methods before `BreatherManager`
  initializes can raise errors.

