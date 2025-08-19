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

    # Decode the 39-byte payload into individual bits (column-major 9×34)
    bits = []
    for byte in captured['vals']:
        for i in range(8):
            bits.append((byte >> i) & 1)
    bits = bits[:9 * 34]

    # Pixels within the glyph bounds should match the input grid
    for x in range(grid.width):
        for y in range(grid.height):
            idx = x + 9 * y
            assert bits[idx] == grid.grid[x][y]

    # Pixels outside the glyph bounds should remain off
    for x in range(9):
        for y in range(34):
            if x >= grid.width or y >= grid.height:
                idx = x + 9 * y
                assert bits[idx] == 0
