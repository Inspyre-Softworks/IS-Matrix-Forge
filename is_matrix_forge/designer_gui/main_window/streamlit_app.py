import copy
import json

import streamlit as st


class Frame:
    def __init__(self, grid, duration: float = 1.0) -> None:
        """
        Container for a single animation frame.

        Parameters
        ----------
        grid :
            2D list of ints (0/1) representing pixel on/off state.
        duration :
            Frame duration in seconds.
        """
        self.grid = grid
        self.duration = float(duration)


class PixelGridWeb:
    def __init__(self, width: int = 9, height: int = 34) -> None:
        """
        Web-based pixel-grid animation editor.

        Parameters
        ----------
        width :
            Number of columns in the grid.
        height :
            Number of rows in the grid.
        """
        self.width = width
        self.height = height

        if 'frames' not in st.session_state:
            st.session_state.frames = [Frame(self._new_grid())]

        if 'current_frame' not in st.session_state:
            st.session_state.current_frame = 0

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _new_grid(self) -> list[list[int]]:
        """Create a new, empty grid."""
        return [[0 for _ in range(self.height)] for _ in range(self.width)]

    def _shift_grid(self, grid: list[list[int]], dx: int, dy: int) -> list[list[int]]:
        """
        Shift the entire grid by (dx, dy).

        Pixels that move out of bounds are discarded; no wrapping.

        Parameters
        ----------
        grid :
            2D list of ints (0/1) to shift.
        dx :
            Horizontal delta; positive moves right, negative moves left.
        dy :
            Vertical delta; positive moves down, negative moves up.

        Returns
        -------
        list[list[int]]
            New shifted grid.
        """
        new_grid = [[0 for _ in range(self.height)] for _ in range(self.width)]

        for x in range(self.width):
            for y in range(self.height):
                if grid[x][y]:
                    nx = x + dx
                    ny = y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        new_grid[nx][ny] = 1

        return new_grid

    # --------------------------------------------------------------------- #
    # Properties over session_state
    # --------------------------------------------------------------------- #

    @property
    def frames(self) -> list[Frame]:
        return st.session_state.frames

    @frames.setter
    def frames(self, value: list[Frame]) -> None:
        st.session_state.frames = value

    @property
    def current_frame(self) -> int:
        return st.session_state.current_frame

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        st.session_state.current_frame = int(value)

    @property
    def grid(self) -> list[list[int]]:
        return self.frames[self.current_frame].grid

    # --------------------------------------------------------------------- #
    # UI
    # --------------------------------------------------------------------- #

    def draw(self) -> None:
        st.title('PixelGrid Animator')

        st.write(f'Frame {self.current_frame + 1}/{len(self.frames)}')

        # Quick overview of frames + durations
        with st.expander('Frames overview / bulk tools', expanded=False):
            st.write('**Durations (seconds):**')
            for idx, frame in enumerate(self.frames):
                st.write(f'- Frame {idx + 1}: {frame.duration:.3f}s')

            st.markdown('---')

            bulk_col1, bulk_col2 = st.columns(2)
            with bulk_col1:
                bulk_duration = st.number_input(
                    'Set all durations to (s)',
                    min_value=0.01,
                    value=1.0,
                    step=0.05,
                    key='bulk_duration_value',
                )
                if st.button('Apply to all frames', key='bulk_set'):
                    for frame in self.frames:
                        frame.duration = bulk_duration
                    st.success('Updated all frame durations.')

            with bulk_col2:
                scale_factor = st.number_input(
                    'Scale all durations by ×',
                    min_value=0.1,
                    value=1.0,
                    step=0.1,
                    key='bulk_scale_value',
                )
                if st.button('Scale all durations', key='bulk_scale'):
                    for frame in self.frames:
                        frame.duration *= scale_factor
                    st.success('Scaled all frame durations.')

            st.markdown('---')

            # Multi-delete
            indices = [f'Frame {i + 1}' for i in range(len(self.frames))]
            to_delete = st.multiselect(
                'Delete selected frame(s)',
                options=indices,
                default=[],
            )
            if st.button('Delete selected frames', key='bulk_delete') and to_delete:
                delete_idxs = sorted(
                    [indices.index(label) for label in to_delete],
                    reverse=True,
                )
                for idx in delete_idxs:
                    # Avoid deleting the last remaining frame
                    if len(self.frames) > 1:
                        self.frames.pop(idx)
                self.current_frame = min(self.current_frame, len(self.frames) - 1)
                st.success('Deleted selected frames.')

        # Render grid
        grid = self.grid
        for row in range(self.height):
            cols = st.columns(self.width)
            for col in range(self.width):
                key = f'pix_{col}_{row}_{self.current_frame}'
                is_on = grid[col][row]
                label = '🟩' if is_on else '⬛'
                if cols[col].button(label, key=key, use_container_width=True):
                    grid[col][row] ^= 1  # Toggle

        st.markdown('---')

        # Per-frame duration editor
        dur_col1, dur_col2 = st.columns([2, 1])
        with dur_col1:
            cur_duration = self.frames[self.current_frame].duration
            new_duration = st.number_input(
                'Current frame duration (seconds)',
                min_value=0.01,
                value=float(cur_duration),
                step=0.05,
                key=f'duration_{self.current_frame}',
            )
            self.frames[self.current_frame].duration = new_duration
        with dur_col2:
            st.write('')
            st.write(f'**#{self.current_frame + 1}**')

        # Frame navigation / add / delete
        c1, c2, c3, c4 = st.columns(4)
        if c1.button('Prev', disabled=self.current_frame == 0):
            self.current_frame -= 1
        if c2.button('Next', disabled=self.current_frame == len(self.frames) - 1):
            self.current_frame += 1
        if c3.button('Add Frame'):
            self.frames.append(Frame(copy.deepcopy(self.grid), duration=self.frames[self.current_frame].duration))
            self.current_frame = len(self.frames) - 1
        if c4.button('Delete Frame', disabled=len(self.frames) == 1):
            self.frames.pop(self.current_frame)
            self.current_frame = max(0, self.current_frame - 1)

        st.markdown('---')

        # Auto-generate motion frames
        with st.expander('Auto-generate motion frames', expanded=False):
            base_idx = st.number_input(
                'Base frame #',
                min_value=1,
                max_value=len(self.frames),
                value=self.current_frame + 1,
                step=1,
                key='motion_base_idx',
            )
            dx = st.number_input('Δx per step (right = +, left = -)', value=1, step=1, key='motion_dx')
            dy = st.number_input('Δy per step (down = +, up = -)', value=0, step=1, key='motion_dy')
            steps = st.number_input('Number of steps/frames to generate', min_value=1, max_value=200, value=1, step=1)
            copy_dur = st.checkbox('Copy duration from base frame', value=True)
            default_dur = st.number_input(
                'Duration to use (if not copying)',
                min_value=0.01,
                value=1.0,
                step=0.05,
                key='motion_default_dur',
            )

            if st.button('Generate motion frames', key='motion_generate'):
                base_frame = self.frames[int(base_idx) - 1]
                base_grid = copy.deepcopy(base_frame.grid)
                dur = base_frame.duration if copy_dur else default_dur

                for step_idx in range(1, int(steps) + 1):
                    shifted = self._shift_grid(base_grid, dx * step_idx, dy * step_idx)
                    self.frames.append(Frame(shifted, duration=dur))

                st.success(f'Generated {int(steps)} motion frame(s) and appended them.')

        st.markdown('---')

        # Export / import
        exp1, exp2, exp3 = st.columns(3)

        # Export: include grid + duration for each frame
        export_payload = [
            {'grid': frame.grid, 'duration': frame.duration}
            for frame in self.frames
        ]
        exp1.download_button(
            'Download JSON',
            data=json.dumps(export_payload, indent=2),
            file_name='frames.json',
            mime='application/json',
        )

        # Import: accept both old (list of grids) and new (list of dicts)
        uploaded = exp2.file_uploader('Load JSON', type='json')
        if uploaded:
            raw = json.load(uploaded)
            new_frames: list[Frame] = []

            if isinstance(raw, list):
                for entry in raw:
                    if isinstance(entry, dict):
                        grid = entry.get('grid')
                        duration = float(entry.get('duration', 1.0))
                    else:
                        # Old style: plain grid list
                        grid = entry
                        duration = 1.0

                    if isinstance(grid, list):
                        new_frames.append(Frame(copy.deepcopy(grid), duration=duration))

            if new_frames:
                self.frames = new_frames
                self.current_frame = 0
                st.success(f'Loaded {len(new_frames)} frame(s) from JSON.')
            else:
                st.error('JSON did not look like a valid frame list.')

        # Placeholder for "Send to Matrix"
        if exp3.button('Send to Matrix'):
            st.info('This would send to your matrix (not implemented here)!')


def main() -> None:
    pg = PixelGridWeb()
    pg.draw()


if __name__ == '__main__':
    main()
