from __future__ import annotations

import contextlib
from types import SimpleNamespace

from is_matrix_forge.led_matrix.scripts.led_matrix import support


class DummyDevice:
    def __init__(
        self,
        *,
        name="COM7",
        device="COM7",
        description="Framework LED Matrix",
        serial_number="FRAK1234",
        location="1-3.3:x.4",
        manufacturer="Framework",
        product="LED Matrix",
        hwid="USB VID:PID=32AC:0020",
        vid=0x32AC,
        pid=0x20,
    ):
        self.name = name
        self.device = device
        self.description = description
        self.serial_number = serial_number
        self.location = location
        self.manufacturer = manufacturer
        self.product = product
        self.hwid = hwid
        self.vid = vid
        self.pid = pid


def test_build_controller_info_report_includes_firmware(monkeypatch):
    monkeypatch.setattr(support, "_query_firmware_version", lambda device: "1.2.3")
    monkeypatch.setattr(
        support,
        "resolve_device_location",
        lambda device: {"abbrev": "R2", "side": "right", "slot": 2},
    )

    report = support.build_controller_info_report([DummyDevice()])

    assert "Detected matrices: 1" in report
    assert "location: R2 (right slot 2)" in report
    assert "firmware_version: 1.2.3" in report


def test_build_version_output_shows_update_message(monkeypatch):
    monkeypatch.setattr(
        support,
        "get_version_snapshot",
        lambda: {
            "package_name": "IS-Matrix-Forge",
            "display_version": "1.0.0-dev.29",
            "source_version": "1.0.0-dev.29",
            "installed_version": "1.0.0.dev28",
        },
    )
    monkeypatch.setattr(
        support,
        "safe_check_for_updates",
        lambda timeout=3.0: {"message": "Update available on PyPI: 1.0.0.dev30."},
    )

    output = support.build_version_output(check_updates=True)

    assert "IS-Matrix-Forge 1.0.0-dev.29" in output
    assert "Installed distribution version: 1.0.0.dev28" in output
    assert "Update available on PyPI: 1.0.0.dev30." in output


def test_build_ticket_info_report_includes_selection_and_copyable_sections(monkeypatch):
    monkeypatch.setattr(
        support,
        "get_version_snapshot",
        lambda: {
            "package_name": "IS-Matrix-Forge",
            "display_version": "1.0.0-dev.29",
            "source_version": "1.0.0-dev.29",
            "installed_version": "1.0.0.dev28",
        },
    )
    monkeypatch.setattr(support, "get_devices", lambda: [DummyDevice()])
    monkeypatch.setattr(
        support,
        "resolve_device_location",
        lambda device: {"abbrev": "L1", "side": "left", "slot": 1},
    )
    monkeypatch.setattr(
        support,
        "safe_check_for_updates",
        lambda timeout=3.0: {"message": "PyPI is up to date for the installed distribution (latest: 1.0.0.dev28)."},
    )
    monkeypatch.setattr(support, "_query_firmware_version", lambda device: "1.2.3")

    args = SimpleNamespace(only_left=True, only_right=False)
    report = support.build_ticket_info_report(args)

    assert "IS-Matrix-Forge Ticket Info" in report
    assert "Matrix selection: the leftmost LED matrix" in report
    assert "Update check: PyPI is up to date for the installed distribution" in report
    assert "firmware_version: 1.2.3" in report


def test_build_ticket_info_markdown_report(monkeypatch):
    monkeypatch.setattr(
        support,
        "get_version_snapshot",
        lambda: {
            "package_name": "IS-Matrix-Forge",
            "display_version": "1.0.0-dev.29",
            "source_version": "1.0.0-dev.29",
            "installed_version": "1.0.0.dev28",
        },
    )
    monkeypatch.setattr(support, "get_devices", lambda: [DummyDevice()])
    monkeypatch.setattr(
        support,
        "resolve_device_location",
        lambda device: {"abbrev": "R1", "side": "right", "slot": 1},
    )
    monkeypatch.setattr(
        support,
        "safe_check_for_updates",
        lambda timeout=3.0: {"message": "Update available on PyPI: 1.0.0.dev30."},
    )
    monkeypatch.setattr(support, "_query_firmware_version", lambda device: "1.2.3")

    report = support.build_ticket_info_report(format="markdown")

    assert report.startswith("# IS-Matrix-Forge Ticket Info")
    assert "- **Update check:** Update available on PyPI: 1.0.0.dev30." in report
    assert "### Matrix 1" in report
    assert "- **firmware_version:** 1.2.3" in report


def test_safe_check_for_updates_reports_source_tree_newer_than_pypi(monkeypatch):
    class FakePyPiVersionInfo:
        def __init__(self, package_name, include_pre_release_for_update_check=False):
            self.package_name = package_name
            self.include_pre_release_for_update_check = include_pre_release_for_update_check
            self.latest_pre_release = "1.0.0.dev28"
            self.latest_stable = "1.0.0.dev27"
            self.latest = "1.0.0.dev28"
            self.installed = "1.0.0.dev28"
            self.newer_available_version = None
            self.installed_newer_than_latest = False

        def check_for_update(self):
            return False

    monkeypatch.setattr(
        support,
        "get_version_snapshot",
        lambda: {
            "package_name": "IS-Matrix-Forge",
            "display_version": "1.0.0-dev.29",
            "source_version": "1.0.0-dev.29",
            "installed_version": "1.0.0.dev28",
        },
    )
    monkeypatch.setattr(support, "_pypi_request_timeout", lambda timeout: contextlib.nullcontext())

    import inspyre_toolbox.ver_man as ver_man

    monkeypatch.setattr(ver_man, "PyPiVersionInfo", FakePyPiVersionInfo)

    result = support.safe_check_for_updates()

    assert result["status"] == "local-newer-than-pypi"
    assert "Installed distribution matches the latest PyPI release (1.0.0.dev28)." in result["message"]
    assert "Current source tree version 1.0.0-dev.29 is newer than the latest PyPI release 1.0.0.dev28." in result["message"]


def test_safe_check_for_updates_uses_installed_newer_than_latest(monkeypatch):
    class FakePyPiVersionInfo:
        def __init__(self, package_name, include_pre_release_for_update_check=False):
            self.package_name = package_name
            self.include_pre_release_for_update_check = include_pre_release_for_update_check
            self.latest_pre_release = "1.0.0.dev28"
            self.latest_stable = "1.0.0.dev27"
            self.latest = "1.0.0.dev28"
            self.installed = "1.0.0.dev29"
            self.newer_available_version = None
            self.installed_newer_than_latest = True

        def check_for_update(self):
            return False

    monkeypatch.setattr(
        support,
        "get_version_snapshot",
        lambda: {
            "package_name": "IS-Matrix-Forge",
            "display_version": "1.0.0-dev.29",
            "source_version": "1.0.0-dev.29",
            "installed_version": "1.0.0.dev29",
        },
    )
    monkeypatch.setattr(support, "_pypi_request_timeout", lambda timeout: contextlib.nullcontext())

    import inspyre_toolbox.ver_man as ver_man

    monkeypatch.setattr(ver_man, "PyPiVersionInfo", FakePyPiVersionInfo)

    result = support.safe_check_for_updates()

    assert result["status"] == "local-newer-than-pypi"
    assert "Installed distribution version 1.0.0.dev29 is newer than the latest PyPI release 1.0.0.dev28." in result["message"]
