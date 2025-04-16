import time
import numpy as np

# Color palette for drawing - displayed vertically on the right side
COLOR_PALETTE = [
    (255, 0, 0),    # Blue   (BGR format)
    (0, 255, 0),    # Green
    (0, 0, 255),    # Red
    (255, 255, 0),  # Cyan
    (255, 0, 255),  # Magenta
    (0, 255, 255),  # Yellow
    (255, 255, 255) # White
]

class DrawingBoard:
    """
    A virtual drawing board for gesture-based interaction using pose estimation.

    The board provides a persistent canvas where users can draw using hand gestures.
    Features:
    - Multi-user support with unique tracking IDs
    - Color palette selection using right hand
    - Drawing activation using left hand position (above shoulders)
    - T-pose gesture for canvas reset
    - Support for multiple WLED panels

    Drawing Controls:
    - Left hand above shoulders: Enables drawing mode
    - Right hand: Acts as drawing pointer
    - Right hand in palette area: Selects color
    - T-pose for 5 seconds: Resets canvas

    Attributes:
        width (int): Total width of the drawing board in pixels
        height (int): Height of the drawing board in pixels
        canvas (np.ndarray): Persistent drawing canvas (height × width × 3)
        PALETTE_WIDTH (int): Width of the color palette area in pixels
    """

    def __init__(self, width=20, height=20):
        """
        Initialize the drawing board with specified dimensions.

        Args:
            width (int): Board width in pixels
            height (int): Board height in pixels
        """
        self.width = width
        self.height = height

        # Initialize empty canvas (black background)
        self.canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Dictionary to track multiple players: {track_id: player_data}
        self.players = {}

        # T-pose detection configuration
        self.tpose_start_time = {}      # Track when each player started T-pose
        self.tpose_threshold = 3.0      # Seconds to hold T-pose for reset
        self.tpose_warning_time = 1.0   # Seconds before warning flash
        self.tpose_y_tolerance = self.height * 0.1  # Vertical tolerance for T-pose

        # Color palette configuration
        self.PALETTE_WIDTH = max(3, self.width // 15)  # Minimum 3 pixels wide
        self.color_tab_height = max(1, self.height // len(COLOR_PALETTE))

    def update_player_pose(self, track_id, left_wrist, right_wrist,
                          left_shoulder, right_shoulder, left_hip, right_hip):
        """
        Update pose data for a specific player.

        Args:
            track_id (int): Unique player identifier
            left_wrist, right_wrist, left_shoulder, right_shoulder, left_hip, right_hip (tuple):
                (x, y) coordinates for each body keypoint in pixel space, can be None if not detected
        """

        if track_id not in self.players:
            # Initialize new player with default white color
            self.players[track_id] = {
                'left_wrist': left_wrist,
                'right_wrist': right_wrist,
                'left_shoulder': left_shoulder,
                'right_shoulder': right_shoulder,
                'left_hip': left_hip,
                'right_hip': right_hip,
                'drawing_enabled': False,
                'color': (255, 255, 255)  # default: white
            }
        else:
            # Update existing player's pose data
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
        Process all players' states and update the canvas.
        """
        now = time.time()

        for track_id, data in list(self.players.items()):
            lw = data['left_wrist']
            rw = data['right_wrist']
            ls = data['left_shoulder']
            rs = data['right_shoulder']
            lh = data['left_hip']
            rh = data['right_hip']

            # Skip processing if essential landmarks are missing
            if None in (lw, rw, ls, rs):
                continue

            # Enable drawing when left wrist is above shoulders
            shoulder_y = min(ls[1], rs[1])
            data['drawing_enabled'] = lw[1] < shoulder_y

            # Color selection from palette
            if rw[0] >= self.width - self.PALETTE_WIDTH:
                palette_index = min(rw[1] // self.color_tab_height,
                                  len(COLOR_PALETTE) - 1)
                data['color'] = COLOR_PALETTE[palette_index]

            # Draw if enabled
            if data['drawing_enabled']:
                x, y = rw
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.canvas[y, x] = data['color']

            # T-pose reset handling
            if self.is_tpose(track_id, data):
                if track_id not in self.tpose_start_time:
                    print(f"T-pose started: track_id={track_id}")
                    self.tpose_start_time[track_id] = now

                elapsed = now - self.tpose_start_time[track_id]
                # Warning flash after 2 seconds
                if elapsed > self.tpose_warning_time:
                    if int(elapsed) % 2 == 1:
                        self.canvas[:] = 255 - self.canvas

                # Reset after 5 seconds
                if elapsed > self.tpose_threshold:
                    print(f"Canvas reset: track_id={track_id}")
                    self.canvas[:] = 0
                    self.tpose_start_time[track_id] = now
            else:
                if track_id in self.tpose_start_time:
                    print(f"T-pose ended: track_id={track_id}")
                    del self.tpose_start_time[track_id]

    def get_frame(self):
        """
        Generate the final frame for display.
        """
        frame = self.canvas.copy()

        # Draw color palette
        for i, color in enumerate(COLOR_PALETTE):
            y_start = i * self.color_tab_height
            y_end = min((i + 1) * self.color_tab_height, self.height)
            frame[y_start:y_end, -self.PALETTE_WIDTH:] = color

        # Draw player cursors
        for data in self.players.values():
            if data['right_wrist'] is not None:  # Only draw cursor if right wrist is detected
                x, y = data['right_wrist']
                if 0 <= x < self.width and 0 <= y < self.height:
                    frame[y, x] = data['color']

        return frame

    def is_tpose(self, track_id, data):
        """
        Check if a player is in T-pose position.

        Args:
            track_id (int): Player identifier
            data (dict): Player pose data

        Returns:
            bool: True if player is in T-pose position

        T-pose criteria:
        - Left to right ordering: LW < LS < RS < RW
        - Wrists at shoulder height (within tolerance)
        """
        lw = data['left_wrist']
        rw = data['right_wrist']
        ls = data['left_shoulder']
        rs = data['right_shoulder']

        # Check if any required landmark is missing
        if None in (lw, rw, ls, rs):
            return False

        # Check horizontal ordering
        horizontal_correct = (lw[0] < ls[0] < rs[0] < rw[0])

        # Check vertical alignment
        y_correct = (abs(lw[1] - ls[1]) <= self.tpose_y_tolerance and
                    abs(rw[1] - rs[1]) <= self.tpose_y_tolerance)

        return horizontal_correct and y_correct