from __future__ import annotations

import pytest

from is_matrix_forge.led_matrix import hardware
from is_matrix_forge.led_matrix.commands.map import CommandVals
from is_matrix_forge.led_matrix.constants import FWK_MAGIC, HEIGHT, WIDTH


class DummyPort:
    """Minimal serial-port descriptor accepted by the hardware layer."""

    device = 'COM_TEST'


class FakeSerial:
    """Capture serial transactions without opening physical hardware."""

    instances = []

    def __init__(self, port, baudrate):
        """Record constructor arguments and initialize captured writes."""
        self.port = port
        self.baudrate = baudrate
        self.writes = []
        self.__class__.instances.append(self)

    def __enter__(self):
        """Return this fake as a context-managed serial stream."""
        return self

    def __exit__(self, exc_type, exc, traceback):
        """Propagate exceptions raised inside the serial context."""
        return False

    def write(self, payload):
        """Capture and report a complete serial write."""
        self.writes.append(bytes(payload))
        return len(payload)


def raw_grid(fill=0):
    """Return a valid 9×34 raw brightness grid."""
    return [[fill for _ in range(HEIGHT)] for _ in range(WIDTH)]


def test_set_framebuffer_brightness_stages_all_columns_then_commits(monkeypatch):
    """A framebuffer transaction stages nine columns before one commit."""
    FakeSerial.instances.clear()
    monkeypatch.setattr(hardware.serial, 'Serial', FakeSerial)
    grid = raw_grid()
    grid[2][7] = 123

    hardware.set_framebuffer_brightness(DummyPort(), grid)

    stream = FakeSerial.instances[-1]
    assert stream.port == DummyPort.device
    assert len(stream.writes) == WIDTH + 1
    for x in range(WIDTH):
        assert stream.writes[x] == bytes(
            FWK_MAGIC + [CommandVals.StageGreyCol, x] + grid[x]
        )
    assert stream.writes[-1] == bytes(
        FWK_MAGIC + [CommandVals.DrawGreyColBuffer, 0x00]
    )


@pytest.mark.parametrize(
    'grid, error',
    [
        ([[0] * HEIGHT for _ in range(WIDTH - 1)], ValueError),
        ([[0] * (HEIGHT - 1) for _ in range(WIDTH)], ValueError),
        ([[0] * HEIGHT for _ in range(WIDTH - 1)] + [['bad'] * HEIGHT], TypeError),
        ([[0] * HEIGHT for _ in range(WIDTH - 1)] + [[256] * HEIGHT], ValueError),
    ],
)
def test_framebuffer_validation_rejects_malformed_grids(grid, error):
    """Malformed dimensions, types, and values are rejected before serial IO."""
    with pytest.raises(error):
        hardware.normalize_framebuffer_brightness_grid(grid)


def test_framebuffer_input_is_copied_before_serial_io(monkeypatch):
    """Caller mutation during IO cannot alter the normalized transaction."""
    class MutatingSerial(FakeSerial):
        """Mutate caller input after each captured packet."""

        def write(self, payload):
            """Capture a packet, mutate input, and report success."""
            result = super().write(payload)
            source[1][1] = 255
            return result

    MutatingSerial.instances.clear()
    monkeypatch.setattr(hardware.serial, 'Serial', MutatingSerial)
    source = raw_grid()

    hardware.set_framebuffer_brightness(DummyPort(), source)

    stream = MutatingSerial.instances[-1]
    assert stream.writes[1][4 + 1] == 0


def test_partial_serial_write_does_not_commit(monkeypatch):
    """A partial column write aborts before commit and disconnects the device."""
    disconnected = []

    class PartialSerial(FakeSerial):
        """Simulate a short serial write."""

        def write(self, payload):
            """Capture a packet while reporting one missing byte."""
            self.writes.append(bytes(payload))
            return len(payload) - 1

    PartialSerial.instances.clear()
    monkeypatch.setattr(hardware.serial, 'Serial', PartialSerial)
    monkeypatch.setattr(hardware, 'disconnect_dev', disconnected.append)

    with pytest.raises(IOError, match='Only wrote'):
        hardware.set_framebuffer_brightness(DummyPort(), raw_grid())

    assert len(PartialSerial.instances[-1].writes) == 1
    assert disconnected == [DummyPort.device]
