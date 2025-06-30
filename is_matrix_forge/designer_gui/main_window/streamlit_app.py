import streamlit as st
import json
import copy

class Frame:
    def __init__(self, grid, duration=1.0):
        self.grid = grid
        self.duration = duration

class PixelGridWeb:
    def __init__(self, width=9, height=34):
        self.width = width
        self.height = height
        if "frames" not in st.session_state:
            st.session_state.frames = [Frame(self._new_grid())]
        if "current_frame" not in st.session_state:
            st.session_state.current_frame = 0

    def _new_grid(self):
        return [[0 for _ in range(self.height)] for _ in range(self.width)]

    @property
    def frames(self):
        return st.session_state.frames

    @frames.setter
    def frames(self, value):
        st.session_state.frames = value

    @property
    def current_frame(self):
        return st.session_state.current_frame

    @current_frame.setter
    def current_frame(self, value):
        st.session_state.current_frame = value

    @property
    def grid(self):
        return self.frames[self.current_frame].grid

    def draw(self):
        st.title("PixelGrid Animator")
        st.write(f"Frame {self.current_frame+1}/{len(self.frames)}")
        # Render grid
        grid = self.grid
        for row in range(self.height):
            cols = st.columns(self.width)
            for col in range(self.width):
                key = f"pix_{col}_{row}_{self.current_frame}"
                is_on = grid[col][row]
                label = "🟩" if is_on else "⬛"
                if cols[col].button(label, key=key, use_container_width=True):
                    grid[col][row] ^= 1  # Toggle

        # Frame controls
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("Prev", disabled=self.current_frame == 0):
            self.current_frame -= 1
        if c2.button("Next", disabled=self.current_frame == len(self.frames)-1):
            self.current_frame += 1
        if c3.button("Add Frame"):
            self.frames.append(Frame(copy.deepcopy(self.grid)))
            self.current_frame = len(self.frames) - 1
        if c4.button("Delete Frame", disabled=len(self.frames) == 1):
            self.frames.pop(self.current_frame)
            self.current_frame = max(0, self.current_frame-1)
        # Export/import
        st.markdown("---")
        exp1, exp2, exp3 = st.columns(3)
        if exp1.button("Export JSON"):
            st.download_button(
                "Download JSON",
                data=json.dumps([f.grid for f in self.frames]),
                file_name="frames.json",
                mime="application/json"
            )
        uploaded = exp2.file_uploader("Load JSON", type="json")
        if uploaded:
            data = json.load(uploaded)
            if isinstance(data, list) and all(isinstance(frame, list) for frame in data):
                self.frames = [Frame(copy.deepcopy(g)) for g in data]
                self.current_frame = 0
        # Placeholder for "Send to Matrix"
        if exp3.button("Send to Matrix"):
            st.info("This would send to your matrix (not implemented here)!")

def main():
    pg = PixelGridWeb()
    pg.draw()

if __name__ == "__main__":
    main()
