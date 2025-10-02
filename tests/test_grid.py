# tests/test_grid.py

import pytest
from unittest.mock import Mock

from is_matrix_forge.led_matrix.display.grid.base import Grid, MATRIX_WIDTH, MATRIX_HEIGHT
from is_matrix_forge.assets.font_map.base import FontMap

# Mocks for helpers/constants
import is_matrix_forge.led_matrix.display.grid.base as grid_mod

@pytest.fixture(autouse=True)
def patch_helpers(monkeypatch):
    # Patch is_valid_grid and generate_blank_grid to use real logic for most tests
    monkeypatch.setattr(grid_mod, "is_valid_grid", lambda g, w, h: (
        isinstance(g, list) and len(g) == w and all(isinstance(col, list) and len(col) == h and all(v in (0, 1) for v in col) for col in g)
    ))
    monkeypatch.setattr(grid_mod, "generate_blank_grid", lambda width, height, fill_value: [[fill_value for _ in range(height)] for _ in range(width)])
    yield

@pytest.mark.parametrize(
    "width,height,fill_value,init_grid,expected_grid",
    [
        # Happy path: default size, fill 0
        (3, 2, 0, None, [[0, 0], [0, 0], [0, 0]]),
        # Happy path: default size, fill 1
        (2, 3, 1, None, [[1, 1, 1], [1, 1, 1]]),
        # Happy path: custom init_grid
        (2, 2, 0, [[1, 0], [0, 1]], [[1, 0], [0, 1]]),
    ],
    ids=[
        "blank_grid_fill_0",
        "blank_grid_fill_1",
        "init_grid_custom"
    ]
)
def test_grid_init_happy(width, height, fill_value, init_grid, expected_grid):
    # Act
    grid = Grid(width=width, height=height, fill_value=fill_value, init_grid=init_grid)

    # Assert
    assert grid.width == width
    assert grid.height == height
    assert grid.fill_value == fill_value
    assert grid.grid == expected_grid


def test_grid_init_from_flat_glyph():
    """Grid should accept a flat 5×6 glyph list and infer dimensions."""
    glyph = [
        0, 0, 0, 0, 0,
        1, 1, 0, 1, 1,
        1, 1, 1, 1, 1,
        0, 1, 1, 1, 0,
        0, 0, 1, 0, 0,
        0, 0, 0, 0, 0,
    ]
    grid = Grid(init_grid=glyph)
    assert grid.width == 5
    assert grid.height == 6
    expected = [[glyph[r * 5 + c] for r in range(6)] for c in range(5)]
    assert grid.grid == expected

@pytest.mark.parametrize(
    "fill_value",
    [
        -1,
        2,
        100,
        "a",
        None,
    ],
    ids=[
        "negative_fill_value",
        "too_large_fill_value",
        "way_too_large_fill_value",
        "string_fill_value",
        "none_fill_value"
    ]
)
def test_grid_init_invalid_fill_value(fill_value):
    # Act & Assert
    with pytest.raises(ValueError, match="fill_value must be 0 or 1"):
        Grid(width=2, height=2, fill_value=fill_value)

def test_grid_init_invalid_init_grid(monkeypatch):
    # Arrange
    def always_false(*a, **kw): return False
    monkeypatch.setattr(grid_mod, "is_valid_grid", always_false)

    # Act & Assert
    with pytest.raises(ValueError, match="init_grid must be 2×2 column-major 0/1 list"):
        Grid(width=2, height=2, fill_value=0, init_grid=[[1, 2], [3, 4]])

def test_grid_grid_property_and_setter():
    # Arrange
    grid = Grid(width=2, height=2, fill_value=0)
    new_grid = [[1, 0], [0, 1]]

    # Act
    grid.grid = new_grid

    # Assert
    assert grid.grid == new_grid
    # Defensive copy
    assert grid.grid is not new_grid
    assert grid.grid[0] is not new_grid[0]

def test_grid_grid_setter_invalid(monkeypatch):
    # Arrange
    grid = Grid(width=2, height=2, fill_value=0)
    monkeypatch.setattr(grid_mod, "is_valid_grid", lambda *a, **kw: False)

    # Act & Assert
    with pytest.raises(ValueError, match="grid must be 2×2 column-major 0/1 list"):
        grid.grid = [[1, 2], [3, 4]]

def test_grid_fill_value_setter_valid():
    # Arrange
    grid = Grid(width=2, height=2, fill_value=0)

    # Act
    grid.fill_value = 1

    # Assert
    assert grid.fill_value == 1

@pytest.mark.parametrize(
    "value",
    [
        -1,
        2,
        "a",
        None,
        0.5
    ],
    ids=[
        "negative",
        "too_large",
        "string",
        "none",
        "float"
    ]
)
def test_grid_fill_value_setter_invalid(value):
    # Arrange
    grid = Grid(width=2, height=2, fill_value=0)

    # Act & Assert
    with pytest.raises(ValueError, match="fill_value must be 0 or 1"):
        grid.fill_value = value


def test_font_map_case_insensitive_lookup():
    fm = FontMap({'A': [[1]], '?': [[0]]})
    assert fm.lookup('a') == [[1]]


def test_font_map_case_sensitive_lookup():
    fm = FontMap({'A': [[1]], '?': [[0]]}, case_sensitive=True)
    assert fm.lookup('A') == [[1]]
    assert fm.lookup('a') == [[0]]


def test_font_map_fallback_character_update():
    fm = FontMap({'A': [[1]], '?': [[9]], ' ': [[0]]})
    fm.fallback_char = ' '
    assert fm.lookup('Z') == [[0]]


def test_font_map_missing_fallback_raises():
    with pytest.raises(ValueError):
        FontMap({'A': [[1]]})

def test_grid_cols_rows_aliases():
    # Arrange
    grid = Grid(width=5, height=7, fill_value=0)

    # Assert
    assert grid.cols == 5
    assert grid.rows == 7

@pytest.mark.parametrize(
    "width,height,fill_value,expected",
    [
        (2, 2, 0, [[0, 0], [0, 0]]),
        (3, 1, 1, [[1], [1], [1]]),
    ],
    ids=["2x2_fill0", "3x1_fill1"]
)
def test_load_blank_grid(width, height, fill_value, expected):
    # Act
    result = Grid.load_blank_grid(width=width, height=height, fill_value=fill_value)

    # Assert
    assert result == expected

def test_from_spec_happy():
    # Arrange
    spec = [[1, 0], [0, 1]]

    # Act
    grid = Grid.from_spec(spec)

    # Assert
    assert grid.grid == spec

@pytest.mark.parametrize(
    "raw,frame_number,expected_grid",
    [
        # Single-grid JSON
        ([[[1, 0], [0, 1]]], 0, [[1, 0], [0, 1]]),
        # Frame-list JSON
        ([{"grid": [[1, 1], [0, 0]]}, {"grid": [[0, 0], [1, 1]]}], 1, [[0, 0], [1, 1]]),
    ],
    ids=["single_grid_json", "frame_list_json"]
)
def test_from_file_happy(monkeypatch, raw, frame_number, expected_grid):
    # Arrange
    def fake_load_from_file(filename):
        return raw[0] if isinstance(raw[0], list) else raw
    monkeypatch.setattr(grid_mod, "load_from_file", lambda filename: raw)

    # Act
    grid = Grid.from_file("dummy.json", frame_number=frame_number, width=2, height=2)

    # Assert
    assert grid.grid == expected_grid

def test_from_file_frame_missing_grid(monkeypatch):
    # Arrange
    monkeypatch.setattr(grid_mod, "load_from_file", lambda filename: [{"not_grid": 123}])

    # Act & Assert
    with pytest.raises(ValueError, match="Frame 0 missing 'grid' list"):
        Grid.from_file("dummy.json", frame_number=0, width=2, height=2)

def test_from_file_unsupported_structure(monkeypatch):
    # Arrange
    monkeypatch.setattr(grid_mod, "load_from_file", lambda filename: {"foo": "bar"})

    # Act & Assert
    with pytest.raises(ValueError, match="Unsupported file structure for grid data."):
        Grid.from_file("dummy.json", width=2, height=2)

def test_from_file_invalid_grid(monkeypatch):
    # Arrange
    monkeypatch.setattr(grid_mod, "load_from_file", lambda filename: [[1, 2], [3, 4]])
    monkeypatch.setattr(grid_mod, "is_valid_grid", lambda *a, **kw: False)

    # Act & Assert
    with pytest.raises(ValueError, match="Loaded grid is not 2×2 column-major 0/1 list"):
        Grid.from_file("dummy.json", width=2, height=2)

def test_draw_happy():
    # Arrange
    grid = Grid(width=2, height=2, fill_value=0)
    device = Mock()
    device.draw_grid = Mock()

    # Act
    grid.draw(device)

    # Assert
    device.draw_grid.assert_called_once_with(grid)

def test_draw_missing_draw_grid():
    # Arrange
    grid = Grid(width=2, height=2, fill_value=0)
    device = object()  # No draw_grid

    # Act & Assert
    with pytest.raises(AttributeError, match="device.draw_grid\\(grid\\) not available"):
        grid.draw(device)

def test_draw_draw_grid_not_callable():
    # Arrange
    grid = Grid(width=2, height=2, fill_value=0)
    class Device:
        draw_grid = 123  # Not callable
    device = Device()

    # Act & Assert
    with pytest.raises(AttributeError, match="device.draw_grid\\(grid\\) not available"):
        grid.draw(device)

@pytest.mark.parametrize(
    "x,y,expected",
    [
        (0, 0, 1),
        (1, 1, 1),
    ],
    ids=["top_left", "bottom_right"]
)
def test_get_pixel_value_happy(x, y, expected):
    # Arrange
    grid = Grid(width=2, height=2, fill_value=0, init_grid=[[1, 0], [0, 1]])

    # Act
    value = grid.get_pixel_value(x, y)

    # Assert
    assert value == expected

@pytest.mark.parametrize(
    "x,y",
    [
        (-1, 0),
        (0, -1),
        (2, 0),
        (0, 2),
    ],
    ids=["x_negative", "y_negative", "x_too_large", "y_too_large"]
)
def test_get_pixel_value_out_of_bounds(x, y):
    # Arrange
    grid = Grid(width=2, height=2, fill_value=0)

    # Act & Assert
    with pytest.raises(IndexError, match="out of bounds"):
        grid.get_pixel_value(x, y)

@pytest.mark.parametrize(
    "init_grid,dx,dy,wrap,expected",
    [
        # No shift
        ([[1, 0], [0, 1]], 0, 0, False, [[1, 0], [0, 1]]),
        # Shift right by 1, no wrap
        ([[1, 0], [0, 1]], 1, 0, False, [[0, 0], [1, 0]]),
        # Shift down by 1, no wrap
        ([[1, 0], [0, 1]], 0, 1, False, [[0, 1], [0, 0]]),
        # Shift left by 1, wrap
        ([[1, 0], [0, 1]], -1, 0, True, [[0, 1], [1, 0]]),
        # Shift up by 1, wrap
        ([[1, 0], [0, 1]], 0, -1, True, [[0, 1], [1, 0]]),
    ],
    ids=[
        "no_shift",
        "shift_right_no_wrap",
        "shift_down_no_wrap",
        "shift_left_wrap",
        "shift_up_wrap"
    ]
)
def test_get_shifted(init_grid, dx, dy, wrap, expected):
    # Arrange
    grid = Grid(width=2, height=2, fill_value=0, init_grid=init_grid)

    # Act
    shifted = grid.get_shifted(dx=dx, dy=dy, wrap=wrap)

    # Assert
    assert shifted.grid == expected
    assert shifted.width == grid.width
    assert shifted.height == grid.height
    assert shifted.fill_value == grid.fill_value
