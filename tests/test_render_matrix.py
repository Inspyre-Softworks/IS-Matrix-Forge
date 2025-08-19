from is_matrix_forge.led_matrix.display.grid import Grid
from is_matrix_forge.led_matrix.display.helpers import render_matrix


def test_render_matrix_handles_small_grid(monkeypatch):
    """Rendering a grid smaller than 9×34 should not error."""
    captured = {}

    def fake_send_command(dev, cmd, vals):
        captured['vals'] = vals

    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.display.helpers.send_command',
        fake_send_command,
    )

    glyph = [
        0, 0, 0, 0, 0,
        1, 1, 0, 1, 1,
        1, 1, 1, 1, 1,
        0, 1, 1, 1, 0,
        0, 0, 1, 0, 0,
        0, 0, 0, 0, 0,
    ]
    grid = Grid(init_grid=glyph)

    class DummyDevice:
        def draw_grid(self, grid_obj):
            render_matrix(self, grid_obj.grid if isinstance(grid_obj, Grid) else grid_obj)

    device = DummyDevice()
    grid.draw(device)

    assert len(captured['vals']) == 39
