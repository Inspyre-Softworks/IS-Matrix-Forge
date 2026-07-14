from typing import Union, List

from inspyre_toolbox.syntactic_sweets.classes import validate_type
from is_matrix_forge.led_matrix.display.grid import Grid

from .helpers import load_grid


class CompositeGrid(Grid):
    """
    CompositeGrid overlays a foreground Grid on a background Grid.

    Internally supports a scalable overlay list, but currently only
    uses a single foreground layer.

    Properties:
        background (Grid):
            The base grid being drawn onto.
        foreground (Grid):
            The primary overlay grid.
        invert_on_overlap (bool):
            If True, overlapping pixels invert instead of overwrite.

    Methods:
        render():
            Combine background and foreground into a new Grid.
        draw(device):
            Render and send the composite to the given device.
    """

    def __init__(
        self,
        background: Union[Grid, List[List[int]]],
        foreground: Union[Grid, List[List[int]]],
        invert_on_overlap: bool = False,
    ):
        # Internal scaffolding: background + list of overlays
        self.__background: Grid = load_grid(background)
        self.__overlays: List[Grid] = [load_grid(foreground)]
        self.__invert_on_overlap: bool = invert_on_overlap

    # --- Properties -------------------------------------------------------

    @property
    def background(self) -> Grid:
        """Get or set the background grid."""
        return self.__background

    @background.setter
    def background(self, bg: Union[Grid, List[List[int]]]):
        self.__background = load_grid(bg)

    @property
    def foreground(self) -> Grid:
        """Get or set the foreground grid."""
        return self.__overlays[0]

    @foreground.setter
    def foreground(self, fg: Union[Grid, List[List[int]]]):
        # Keep backward compatibility for now
        self.__overlays = [load_grid(fg)]

    @property
    def invert_on_overlap(self) -> bool:
        """Whether overlapping pixels are inverted instead of overwritten."""
        return self.__invert_on_overlap

    @invert_on_overlap.setter
    @validate_type(bool)
    def invert_on_overlap(self, val: bool):
        self.__invert_on_overlap = val

    # --- Internal Hooks for Future Expansion ------------------------------

    def _add_overlay(self, overlay: Union[Grid, List[List[int]]]) -> None:
        """(Internal) Add another overlay layer — unused in public API yet."""
        self.__overlays.append(load_grid(overlay))

    def _iter_layers(self):
        """
        (Internal) Iterate layers in proper order.
        Currently returns [foreground], but can easily expand.
        """
        # Future: return self.__overlays in stacking order
        yield from self.__overlays

    # --- Core Logic -------------------------------------------------------

    def render(self) -> Grid:
        """
        Build and return a composite Grid with overlays drawn on the background.

        For now, uses only one overlay, but designed for future multiple layers.
        """
        base = self.background.copy()
        invert = self.invert_on_overlap
        base_grid = base._grid

        height = base.height
        width = base.width

        for overlay in self._iter_layers():
            fg_grid = overlay._grid
            h = min(height, overlay.height)
            w = min(width, overlay.width)

            for y in range(h):
                bg_row = base_grid[y]
                fg_row = fg_grid[y]
                for x in range(w):
                    fg_val = fg_row[x]
                    if fg_val:
                        bg_val = bg_row[x]
                        bg_row[x] = 0 if invert and bg_val else fg_val

        return base

    def draw(self, device) -> None:
        """Render and draw the composite grid to the given device."""
        device.draw_grid(self.render())
