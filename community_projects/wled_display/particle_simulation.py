import numpy as np
import cv2

# Constants
SCREEN_WIDTH = 40
SCREEN_HEIGHT = 20
FPS = 30
MAX_PARTICLES = 200
PARTICLE_LIFETIME = 10
PARTICLE_SPEED_DECAY = 0.8
GLITTER_PROBABILITY = 0.01
HAND_TIMEOUT = 60

# Predefined vibrant colors (BGR format)
VIBRANT_COLORS = [
    (255, 0, 0),    # Red
    (0, 255, 0),    # Green
    (255, 165, 0),  # Orange
    (0, 0, 255),    # Blue
    (255, 255, 0),  # Cyan
    (0, 255, 255),  # Yellow
    (255, 0, 255),  # Magenta
]

class ParticleSimulation:
    def __init__(self):
        self.hands = {}  # Store hand data by hand ID
        self.particles = {
            "positions": np.zeros((MAX_PARTICLES, 2)),
            "velocities": np.zeros((MAX_PARTICLES, 2)),
            "lifetimes": np.zeros(MAX_PARTICLES),
            "start_colors": np.zeros((MAX_PARTICLES, 3)),
            "end_colors": np.zeros((MAX_PARTICLES, 3)),
        }
        self.active_particles = 0
        self.frame_count = 0
        self.color_schemes = {}  # Color schemes for each hand

    def generate_color_scheme(self, hand_id):
        """
        Generate a unique color scheme for a given hand_id using predefined vibrant colors.
        """
        start_color = VIBRANT_COLORS[hand_id % len(VIBRANT_COLORS)]
        end_color = VIBRANT_COLORS[(hand_id + 1) % len(VIBRANT_COLORS)]
        return start_color, end_color

    def update_hand_positions(self, hand_data):
        """
        Update hands with new positions.
        `hand_data` should be a dictionary: {hand_id: (x, y)}.
        """
        for hand_id, new_pos in hand_data.items():
            new_pos = np.array(new_pos, dtype=float)
            if hand_id in self.hands:
                self.hands[hand_id]["velocity"] = new_pos - self.hands[hand_id]["position"]
                self.hands[hand_id]["position"] = new_pos
                self.hands[hand_id]["last_seen"] = self.frame_count
            else:
                start_color, end_color = self.generate_color_scheme(hand_id)
                self.color_schemes[hand_id] = {"start": start_color, "end": end_color}
                self.hands[hand_id] = {
                    "position": new_pos,
                    "velocity": np.array([0, 0], dtype=float),
                    "last_seen": self.frame_count,
                }

    def remove_inactive_hands(self):
        """
        Remove hands that have not been updated within the timeout period.
        """
        inactive_hands = [
            hand_id
            for hand_id, hand in self.hands.items()
            if self.frame_count - hand["last_seen"] > HAND_TIMEOUT
        ]
        for hand_id in inactive_hands:
            del self.hands[hand_id]
            del self.color_schemes[hand_id]

    def emit_particles(self):
        """
        Emit particles for each active hand.
        """
        for hand_id, hand in self.hands.items():
            if self.active_particles >= MAX_PARTICLES:
                break
            count = min(MAX_PARTICLES - self.active_particles, 5)  # Emit up to 5 particles per hand
            indices = np.arange(self.active_particles, self.active_particles + count)
            self.particles["positions"][indices] = hand["position"]
            random_velocity = np.random.uniform(-1, 1, (count, 2))
            self.particles["velocities"][indices] = hand["velocity"] * 0.1 + random_velocity * 0.5
            self.particles["lifetimes"][indices] = PARTICLE_LIFETIME
            self.particles["start_colors"][indices] = self.color_schemes[hand_id]["start"]
            self.particles["end_colors"][indices] = self.color_schemes[hand_id]["end"]
            self.active_particles += count

    def update_particles(self):
        """
        Update particles' positions, velocities, and lifetimes.
        """
        if self.active_particles == 0:
            return

        positions = self.particles["positions"][:self.active_particles]
        velocities = self.particles["velocities"][:self.active_particles]
        lifetimes = self.particles["lifetimes"][:self.active_particles]
        start_colors = self.particles["start_colors"][:self.active_particles]
        end_colors = self.particles["end_colors"][:self.active_particles]

        velocities *= PARTICLE_SPEED_DECAY
        positions += velocities
        lifetimes -= 1

        alive = lifetimes > 0
        self.active_particles = np.sum(alive)
        self.particles["positions"][:self.active_particles] = positions[alive]
        self.particles["velocities"][:self.active_particles] = velocities[alive]
        self.particles["lifetimes"][:self.active_particles] = lifetimes[alive]
        self.particles["start_colors"][:self.active_particles] = start_colors[alive]
        self.particles["end_colors"][:self.active_particles] = end_colors[alive]

    def draw_particles(self, frame):
        """
        Draw particles as single pixels on the frame.
        """
        for i in range(self.active_particles):
            x, y = self.particles["positions"][i]
            if np.random.random() < GLITTER_PROBABILITY:
                color = (255, 255, 255)  # Glitter: Bright white
            else:
                start_color = self.particles["start_colors"][i]
                end_color = self.particles["end_colors"][i]
                fraction = 1 - (self.particles["lifetimes"][i] / PARTICLE_LIFETIME)
                color = start_color + (end_color - start_color) * fraction
                color = tuple(map(int, color))  # Convert to tuple of integers

            if 0 <= int(x) < frame.shape[1] and 0 <= int(y) < frame.shape[0]:
                frame[int(y), int(x)] = color  # Set the pixel color directly

    def get_frame(self, width, height):
        """
        Generate the current particle frame as a NumPy array.
        """
        frame = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
        self.draw_particles(frame)
        return cv2.resize(frame, (width, height))

    def update(self):
        """
        Update frame data and emit particles.
        """
        self.frame_count += 1
        self.remove_inactive_hands()
        self.emit_particles()
        self.update_particles()
