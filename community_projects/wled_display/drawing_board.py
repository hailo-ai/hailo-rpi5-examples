"""
drawing_board.py

Same logic as before, except we now refer to the region as "chest"
instead of "belly button."
We still use a shrunk bounding box around shoulders & hips to confirm
the left wrist is near the center of the body (the 'chest' area).

If multiple panels are used, the total LED width might be panel_width * panels.
The last 3 columns are always reserved for the color palette.
"""

import time
import numpy as np
import cv2

# A vertical color palette on the right side of the final LED matrix
COLOR_PALETTE = [
    (255, 0, 0),    # Blue
    (0, 255, 0),    # Green
    (0, 0, 255),    # Red
    (255, 255, 0),  # Cyan
    (255, 0, 255),  # Magenta
    (0, 255, 255),  # Yellow
    (255, 255, 255) # White
]

class DrawingBoard:
    """
    Maintains a persistent canvas for gesture-based drawing across a
    (width × height) LED matrix, which may span multiple WLED panels horizontally.

    "Chest" check:
      - The left wrist must be inside a shrunk rectangle around (shoulders & hips)
        to enable drawing.
    T-pose:
      - LW < LS < RS < RW horizontally
      - Wrists near shoulders vertically (± self.y_tolerance)
    Color picking in the last 3 columns, single-pixel drawing if enabled.
    """
    def __init__(self, width=20, height=20):
        self.width = width
        self.height = height

        # Persistent canvas
        self.canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Player states
        self.players = {}

        # T-pose detection timing
        self.tpose_start_time = {}
        self.TPOSE_THRESHOLD = 5.0     # hold T-pose for 5s => reset
        self.tpose_warning_time = 2.0  # after 2s => flashing

        # The palette uses the last 3 columns
        self.PALETTE_WIDTH = 3
        self.color_swatch_height = max(1, self.height // len(COLOR_PALETTE))

        # T-pose logic
        self.y_tolerance = 5

        # For the "chest" bounding box shrink
        self.torso_shrink_factor = 0.4

    def update_player_pose(self, track_id, left_wrist, right_wrist,
                           left_shoulder, right_shoulder, left_hip, right_hip):
        """Stores updated landmarks for a given player in pixel coords."""
        if track_id not in self.players:
            self.players[track_id] = {
                'left_wrist': left_wrist,
                'right_wrist': right_wrist,
                'left_shoulder': left_shoulder,
                'right_shoulder': right_shoulder,
                'left_hip': left_hip,
                'right_hip': right_hip,
                'drawing_enabled': False,
                'color': (255, 255, 255)  # default color (white)
            }
        else:
            self.players[track_id].update({
                'left_wrist': left_wrist,
                'right_wrist': right_wrist,
                'left_shoulder': left_shoulder,
                'right_shoulder': right_shoulder,
                'left_hip': left_hip,
                'right_hip': right_hip
            })

    def update(self):
        """
        Main logic for each player:
          1) "Chest" => left wrist in shrunk bounding box => enable drawing
          2) Right wrist color picking if in last 3 columns
          3) Single-pixel drawing if enabled
          4) T-pose => reset after 5s
        """
        now = time.time()

        for track_id, data in list(self.players.items()):
            lw = data['left_wrist']
            rw = data['right_wrist']
            ls = data['left_shoulder']
            rs = data['right_shoulder']
            lh = data['left_hip']
            rh = data['right_hip']

            # 1) "Chest": check if left wrist is in the shrunk bounding box of shoulders & hips
            if self.is_within_torso_shrunk(lw, ls, rs, lh, rh, self.torso_shrink_factor):
                data['drawing_enabled'] = True
            else:
                data['drawing_enabled'] = False

            # 2) Color picking: if right wrist is in the last 3 columns
            if rw[0] >= self.width - self.PALETTE_WIDTH:
                palette_index = rw[1] // self.color_swatch_height
                palette_index = min(palette_index, len(COLOR_PALETTE) - 1)
                data['color'] = COLOR_PALETTE[palette_index]

            # 3) If drawing is enabled, paint 1 pixel
            if data['drawing_enabled']:
                x, y = rw
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.canvas[y, x] = data['color']

            # 4) T-pose detection => reset logic
            if self.is_tpose(track_id, data):
                if track_id not in self.tpose_start_time:
                    print(f"[DEBUG] T-pose START for track_id={track_id}")
                    self.tpose_start_time[track_id] = now

                elapsed = now - self.tpose_start_time[track_id]
                # Flash after 2s
                if elapsed > self.tpose_warning_time:
                    if int(elapsed) % 2 == 1:
                        self.canvas[:] = 255 - self.canvas

                # Reset after 5s
                if elapsed > self.TPOSE_THRESHOLD:
                    print(f"[DEBUG] T-pose RESET for track_id={track_id}")
                    self.canvas[:] = 0
                    self.tpose_start_time[track_id] = now
            else:
                # If T-pose ended
                if track_id in self.tpose_start_time:
                    print(f"[DEBUG] T-pose END for track_id={track_id}")
                    del self.tpose_start_time[track_id]

    def get_frame(self):
        """
        Returns the final frame = persistent canvas + color palette +
        right-wrist marker in the player's color.
        """
        frame = self.canvas.copy()

        # Draw the color palette on the far right side
        for i, color in enumerate(COLOR_PALETTE):
            row_start = i * self.color_swatch_height
            row_end = min((i + 1) * self.color_swatch_height, self.height)
            frame[row_start:row_end, self.width - self.PALETTE_WIDTH : self.width] = color

        # Overlay each player's right wrist in their chosen color
        for data in self.players.values():
            x, y = data['right_wrist']
            if 0 <= x < self.width and 0 <= y < self.height:
                frame[y, x] = data['color']

        return frame

    def is_tpose(self, track_id, data):
        """
        T-pose if x-coords are LW < LS < RS < RW,
        wrists' y-values are within self.y_tolerance of shoulders.
        """
        lw = data['left_wrist']
        rw = data['right_wrist']
        ls = data['left_shoulder']
        rs = data['right_shoulder']

        # Horizontal ordering
        horizontal_correct = (lw[0] < ls[0] < rs[0] < rw[0])

        # Wrists near shoulders in Y
        y_correct = (
            abs(lw[1] - ls[1]) <= self.y_tolerance and
            abs(rw[1] - rs[1]) <= self.y_tolerance
        )

        print(f"[DEBUG] T-pose check track_id={track_id}: "
              f"horizontal_correct={horizontal_correct}, y_correct={y_correct}; "
              f"LW={lw}, LS={ls}, RS={rs}, RW={rw}")

        return horizontal_correct and y_correct

    @staticmethod
    def shrink_bbox(x_min, x_max, y_min, y_max, shrink_factor):
        """
        Given bounding box edges [x_min..x_max], [y_min..y_max],
        shrink them around the center by 'shrink_factor' (0..1).
        If shrink_factor=0.4 => box is 40% of original size,
        centered at the midpoint.
        """
        cx = (x_min + x_max) / 2.0
        cy = (y_min + y_max) / 2.0
        w = x_max - x_min
        h = y_max - y_min

        new_w = w * shrink_factor
        new_h = h * shrink_factor

        x_min_new = cx - new_w / 2
        x_max_new = cx + new_w / 2
        y_min_new = cy - new_h / 2
        y_max_new = cy + new_h / 2

        return x_min_new, x_max_new, y_min_new, y_max_new

    def is_within_torso_shrunk(self, point, ls, rs, lh, rh, shrink_factor=0.9):
        """
        Returns True if 'point' is inside a *shrunk* rectangle
        around the torso points [ls, rs, lh, rh] => 'chest' region.
        """
        x_min = min(ls[0], rs[0], lh[0], rh[0])
        x_max = max(ls[0], rs[0], lh[0], rh[0])
        y_min = min(ls[1], rs[1], lh[1], rh[1])
        y_max = max(ls[1], rs[1], lh[1], rh[1])

        (x_min_s, x_max_s,
         y_min_s, y_max_s) = self.shrink_bbox(x_min, x_max, y_min, y_max, shrink_factor)

        px, py = point
        return (x_min_s <= px <= x_max_s) and (y_min_s <= py <= y_max_s)
