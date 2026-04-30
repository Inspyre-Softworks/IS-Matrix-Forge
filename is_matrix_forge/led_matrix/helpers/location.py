from __future__ import annotations

import re
from typing import Optional, Tuple


class UnknownDeviceLocationError(ValueError):
    """Raised when a device cannot be mapped to a known physical location."""


def _normalize_side(value):
    if isinstance(value, str):
        return value.strip().lower()
    return None


def _safe_getattr(obj, attr: str, default=None):
    try:
        return getattr(obj, attr)
    except Exception:
        return default


def _candidate_location_keys(raw_location) -> tuple[str, ...]:
    if not isinstance(raw_location, str):
        return ()

    normalized = raw_location.strip()
    if not normalized:
        return ()

    candidates = [normalized]

    # Windows/pyserial can append a transport suffix such as ``:x.4``.
    prefix = normalized.split(':', 1)[0].strip()
    if prefix and prefix not in candidates:
        candidates.append(prefix)

    match = re.match(r'^\d+(?:-\d+)+(?:\.\d+)*', prefix or normalized)
    if match:
        compact = match.group(0)
        if compact and compact not in candidates:
            candidates.append(compact)

    return tuple(candidates)


def _build_unknown_location_error(device) -> UnknownDeviceLocationError:
    name = _safe_getattr(device, 'name', '<unknown>')
    raw_location = _safe_getattr(device, 'location')
    serial_number = _safe_getattr(device, 'serial_number', '<unknown>')
    candidates = _candidate_location_keys(raw_location)
    candidate_text = f', normalized_candidates={candidates!r}' if candidates else ''
    return UnknownDeviceLocationError(
        f'Unknown controller location for device {name!r} '
        f'(serial={serial_number!r}, raw_location={raw_location!r}{candidate_text}).'
    )


def resolve_device_location(device, *, strict: bool = False) -> Optional[dict]:
    try:
        from is_matrix_forge.led_matrix.constants import SLOT_MAP
    except Exception:
        SLOT_MAP = {}

    cached_location = _safe_getattr(device, '_matrix_location_info')
    if isinstance(cached_location, dict):
        return cached_location

    device_location = _safe_getattr(device, 'location')
    for candidate in _candidate_location_keys(device_location):
        resolved = SLOT_MAP.get(candidate)
        if isinstance(resolved, dict):
            resolved = dict(resolved)
            try:
                setattr(device, '_matrix_location_info', resolved)
                setattr(device, '_matrix_location_key', candidate)
            except Exception:
                pass
            return resolved

    if strict:
        raise _build_unknown_location_error(device)
    return None


def ensure_device_location(device) -> dict:
    """Resolve and cache device location info, raising when the mapping is unknown."""
    location = resolve_device_location(device, strict=True)
    if not isinstance(location, dict):  # pragma: no cover - strict=True already raises
        raise _build_unknown_location_error(device)
    return location


def resolve_controller_location(controller) -> Tuple[Optional[str], Optional[int]]:
    """
    Return a normalized (side, slot) tuple for a controller.

    Resolution order:
      1) explicit attributes ``side_of_keyboard`` / ``slot`` when safely readable
      2) ``controller.location`` when it is a dict
      3) ``controller.device.location`` via SLOT_MAP
    """
    side = _normalize_side(_safe_getattr(controller, 'side_of_keyboard'))
    slot = _safe_getattr(controller, 'slot')

    location = _safe_getattr(controller, 'location')
    if isinstance(location, dict):
        if side is None:
            side = _normalize_side(location.get('side'))
        if slot is None:
            slot = location.get('slot')

    if side is None or slot is None:
        entry = resolve_device_location(_safe_getattr(controller, 'device'))
        if isinstance(entry, dict):
            side = _normalize_side(side or entry.get('side'))
            slot = slot if slot is not None else entry.get('slot')

    try:
        slot = int(slot) if slot is not None else None
    except (TypeError, ValueError):
        slot = None

    return side, slot
