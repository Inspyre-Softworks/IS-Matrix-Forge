from __future__ import annotations

import contextlib
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from packaging.version import InvalidVersion, Version

from is_matrix_forge.led_matrix.hardware import get_version as get_firmware_version
from is_matrix_forge.led_matrix.helpers.device import get_devices
from is_matrix_forge.led_matrix.helpers.location import resolve_device_location
from is_matrix_forge.version import get_version_snapshot


def _safe_getattr(obj, attr: str, default=None):
    try:
        return getattr(obj, attr)
    except Exception:
        return default


def _desired_side(cli_args) -> Optional[str]:
    if cli_args is None:
        return None
    if getattr(cli_args, "only_left", False):
        return "left"
    if getattr(cli_args, "only_right", False):
        return "right"
    return None


def describe_selection(cli_args) -> str:
    desired = _desired_side(cli_args)
    if desired == "left":
        return "the leftmost LED matrix"
    if desired == "right":
        return "the rightmost LED matrix"
    return "all detected LED matrices"


def _device_side(device) -> Optional[str]:
    location = resolve_device_location(device)
    if isinstance(location, dict):
        side = location.get("side")
        if isinstance(side, str):
            return side.strip().lower()
    return None


def _device_slot_rank(device) -> int:
    location = resolve_device_location(device)
    if isinstance(location, dict):
        try:
            return int(location.get("slot"))
        except (TypeError, ValueError):
            return 0
    return 0


def find_leftmost_device(devices: Iterable) -> Optional[object]:
    ranked = []
    for index, device in enumerate(devices):
        side = _device_side(device)
        if side == "left":
            side_rank = 0
        elif side == "right":
            side_rank = 2
        else:
            side_rank = 1
        ranked.append(((side_rank, _device_slot_rank(device), index), device))

    if not ranked:
        return None
    return min(ranked, key=lambda item: item[0])[1]


def find_rightmost_device(devices: Iterable) -> Optional[object]:
    ranked = []
    for index, device in enumerate(devices):
        side = _device_side(device)
        if side == "right":
            side_rank = 0
        elif side == "left":
            side_rank = 2
        else:
            side_rank = 1
        ranked.append(((side_rank, -_device_slot_rank(device), index), device))

    if not ranked:
        return None
    return min(ranked, key=lambda item: item[0])[1]


def filter_devices_by_side(devices: Iterable, cli_args) -> list:
    device_list = list(devices)
    desired = _desired_side(cli_args)

    if desired is None:
        return device_list

    if desired == "left":
        target = find_leftmost_device(device_list)
        return [target] if target is not None else []

    if desired == "right":
        target = find_rightmost_device(device_list)
        return [target] if target is not None else []

    return device_list


def get_selected_devices(cli_args=None) -> list:
    devices = get_devices()
    if not devices:
        raise SystemExit("No LED matrices are available.")

    if filtered := filter_devices_by_side(devices, cli_args):
        return filtered

    raise SystemExit(f"No LED matrices matched the requested selection ({describe_selection(cli_args)}).")


def _format_hex(value) -> str:
    if isinstance(value, int):
        return f"0x{value:04X}"
    return "Unknown"


def _format_location(device) -> tuple[str, str]:
    resolved = resolve_device_location(device)
    raw_location = str(_safe_getattr(device, "location", "Unknown"))

    if not isinstance(resolved, dict):
        return "Unknown", raw_location

    abbrev = resolved.get("abbrev") or "Unknown"
    side = resolved.get("side") or "unknown"
    slot = resolved.get("slot")
    slot_text = f" slot {slot}" if slot is not None else ""
    return f"{abbrev} ({side}{slot_text})", raw_location


def _query_firmware_version(device) -> str:
    try:
        return str(get_firmware_version(device))
    except Exception as exc:
        return f"Unavailable ({type(exc).__name__}: {exc})"


def _parse_version(version_text: Optional[str]) -> Optional[Version]:
    if not version_text:
        return None

    try:
        return Version(str(version_text).strip())
    except (InvalidVersion, TypeError, ValueError):
        return None


def _is_newer_than_pypi(current_version: Optional[str], latest_version: Optional[str]) -> bool:
    parsed_current = _parse_version(current_version)
    parsed_latest = _parse_version(latest_version)

    if parsed_current is None or parsed_latest is None:
        return False

    return parsed_current > parsed_latest


def _build_device_fields(device, *, include_firmware: bool = True) -> list[tuple[str, str]]:
    resolved_location, raw_location = _format_location(device)
    fields = [
        ("name", str(_safe_getattr(device, "name", "Unknown"))),
        ("serial_port", str(_safe_getattr(device, "device", "Unknown"))),
        ("description", str(_safe_getattr(device, "description", "Unknown"))),
        ("serial_number", str(_safe_getattr(device, "serial_number", "Unknown"))),
        ("location", resolved_location),
        ("raw_location", raw_location),
        ("manufacturer", str(_safe_getattr(device, "manufacturer", "Unknown"))),
        ("product", str(_safe_getattr(device, "product", "Unknown"))),
        ("hwid", str(_safe_getattr(device, "hwid", "Unknown"))),
        ("vid", _format_hex(_safe_getattr(device, "vid"))),
        ("pid", _format_hex(_safe_getattr(device, "pid"))),
    ]

    if include_firmware:
        fields.append(("firmware_version", _query_firmware_version(device)))

    return fields


def build_controller_info_report(devices: Iterable, *, include_firmware: bool = True) -> str:
    device_list = list(devices)
    lines = [f"Detected matrices: {len(device_list)}"]

    for index, device in enumerate(device_list, start=1):
        lines.extend(["", f"Matrix {index}:"])
        for key, value in _build_device_fields(device, include_firmware=include_firmware):
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


@contextlib.contextmanager
def _pypi_request_timeout(timeout: float):
    from inspyre_toolbox.ver_man.classes import pypi as pypi_module

    original_get = pypi_module.requests.get

    def _timed_get(*args, **kwargs):
        kwargs.setdefault("timeout", timeout)
        return original_get(*args, **kwargs)

    pypi_module.requests.get = _timed_get
    try:
        yield
    finally:
        pypi_module.requests.get = original_get


def safe_check_for_updates(*, timeout: float = 3.0) -> dict[str, Optional[str]]:
    try:
        from inspyre_toolbox.ver_man import PyPiVersionInfo

        with _pypi_request_timeout(timeout):
            info = PyPiVersionInfo("IS-Matrix-Forge", include_pre_release_for_update_check=True)

        latest = info.latest_pre_release or info.latest_stable or info.latest
        latest_text = str(latest) if latest is not None else None
        installed = str(info.installed) if info.installed else None
        snapshot = get_version_snapshot()
        source_version = snapshot.get("source_version") or snapshot.get("display_version")
        messages: list[str] = []
        current_status = "up-to-date"

        installed_newer_than_latest = bool(getattr(info, "installed_newer_than_latest", False))

        if installed is None:
            messages.append(
                f"PyPI latest release: {latest_text} (installed distribution metadata unavailable for comparison)."
            )
            current_status = "unavailable"
        elif installed_newer_than_latest or _is_newer_than_pypi(installed, latest_text):
            messages.append(
                f"Installed distribution version {installed} is newer than the latest PyPI release {latest_text}."
            )
            current_status = "local-newer-than-pypi"
        elif info.check_for_update():
            newer_version = str(info.newer_available_version or latest)
            messages.append(f"Update available on PyPI: {newer_version} (installed: {installed}).")
            current_status = "update-available"
        else:
            messages.append(f"Installed distribution matches the latest PyPI release ({latest_text}).")

        if (
            source_version
            and source_version != installed
            and _is_newer_than_pypi(source_version, latest_text)
        ):
            messages.append(
                f"Current source tree version {source_version} is newer than the latest PyPI release {latest_text}."
            )
            current_status = "local-newer-than-pypi"

        return {
            "status": current_status,
            "message": " ".join(messages),
            "latest": latest_text,
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "message": f"PyPI update check unavailable ({type(exc).__name__}: {exc}).",
            "latest": None,
        }


def build_version_output(*, check_updates: bool = False) -> str:
    snapshot = get_version_snapshot()
    lines = [f"{snapshot['package_name']} {snapshot['display_version']}"]

    source_version = snapshot.get("source_version")
    installed_version = snapshot.get("installed_version")

    if source_version and installed_version and source_version != installed_version:
        lines.append(f"Source tree version: {source_version}")
        lines.append(f"Installed distribution version: {installed_version}")
    elif installed_version and installed_version != snapshot["display_version"]:
        lines.append(f"Installed distribution version: {installed_version}")

    if check_updates:
        lines.append(safe_check_for_updates()["message"])
    else:
        lines.append("Run `led-matrix --check-updates` to compare against PyPI.")

    return "\n".join(lines)


def _collect_ticket_info(
    cli_args=None,
    *,
    include_update_check: bool = True,
    include_firmware: bool = True,
) -> dict[str, object]:
    snapshot = get_version_snapshot()
    selected_devices = filter_devices_by_side(get_devices(), cli_args)
    metadata = [
        ("Generated", datetime.now().astimezone().isoformat(timespec="seconds")),
        ("Version", snapshot["display_version"]),
        ("Source tree version", snapshot.get("source_version") or "Unavailable"),
        ("Installed distribution version", snapshot.get("installed_version") or "Unavailable"),
        ("Python", platform.python_version()),
        ("Python executable", sys.executable),
        ("Platform", platform.platform()),
        ("Machine", platform.machine() or "Unknown"),
        ("Working directory", str(Path.cwd())),
        ("Matrix selection", describe_selection(cli_args)),
    ]

    if include_update_check:
        metadata.append(("Update check", safe_check_for_updates()["message"]))
    else:
        metadata.append(("Update check", "Skipped by user request."))

    return {
        "metadata": metadata,
        "devices": list(selected_devices),
        "include_firmware": include_firmware,
    }


def build_ticket_info_markdown_report(
    cli_args=None,
    *,
    include_update_check: bool = True,
    include_firmware: bool = True,
) -> str:
    report_data = _collect_ticket_info(
        cli_args,
        include_update_check=include_update_check,
        include_firmware=include_firmware,
    )
    metadata = report_data["metadata"]
    devices = report_data["devices"]

    lines = ["# IS-Matrix-Forge Ticket Info", ""]
    for key, value in metadata:
        lines.append(f"- **{key}:** {value}")

    lines.append("")
    lines.append("## Matrices")
    lines.append("")

    if devices:
        lines.append(f"- **Detected matrices:** {len(devices)}")
        lines.append("")
        for index, device in enumerate(devices, start=1):
            lines.append(f"### Matrix {index}")
            lines.append("")
            for key, value in _build_device_fields(device, include_firmware=include_firmware):
                lines.append(f"- **{key}:** {value}")
            lines.append("")
    else:
        lines.append("- **Detected matrices:** 0")
        lines.append("- No supported LED matrices matched the current selection.")

    return "\n".join(lines).rstrip()


def build_ticket_info_report(
    cli_args=None,
    *,
    include_update_check: bool = True,
    include_firmware: bool = True,
    format: str = "plain",
) -> str:
    if format == "markdown":
        return build_ticket_info_markdown_report(
            cli_args,
            include_update_check=include_update_check,
            include_firmware=include_firmware,
        )

    if format != "plain":
        raise ValueError(f"Unsupported ticket info format: {format!r}")

    report_data = _collect_ticket_info(
        cli_args,
        include_update_check=include_update_check,
        include_firmware=include_firmware,
    )
    metadata = report_data["metadata"]
    devices = report_data["devices"]

    lines = ["IS-Matrix-Forge Ticket Info"]
    for key, value in metadata:
        lines.append(f"{key}: {value}")

    lines.append("")
    if devices:
        lines.append(build_controller_info_report(devices, include_firmware=include_firmware))
    else:
        lines.append("Detected matrices: 0")
        lines.append("No supported LED matrices matched the current selection.")

    return "\n".join(lines)


def copy_text_to_clipboard(text: str) -> tuple[bool, str]:
    try:
        import clipboard as clipboard_module

        clipboard_module.copy(text)
        return True, "clipboard"
    except Exception:
        pass

    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True, "tkinter"
    except Exception:
        pass

    commands = []
    if sys.platform.startswith("win"):
        commands.extend((["powershell", "-NoProfile", "-Command", "Set-Clipboard"], ["clip"]))
    elif sys.platform == "darwin":
        commands.append(["pbcopy"])
    else:
        commands.extend((["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]))

    for command in commands:
        try:
            subprocess.run(command, input=text, text=True, capture_output=True, check=True)
            return True, " ".join(command)
        except Exception:
            continue

    return False, "No clipboard backend is available in this environment."
