import numpy as np
import cv2

# Predefined colors (BGR format)
COLORS = [
    (0, 0, 255),    # Red
    (0, 255, 0),    # Green
    (0, 165, 255),  # Orange
    (255, 0, 0),    # Blue
    (255, 255, 0),  # Cyan
    (0, 255, 255),  # Yellow
    (255, 0, 255),  # Magenta
]

class ParticleSimulation:
    def __init__(self, screen_width=20, screen_height=20, max_particles=200, particle_lifetime=10,
                 particle_speed_decay=0.8, glitter_probability=0.01, player_timeout=60, particle_size=1):
        self.SCREEN_WIDTH = screen_width
        self.SCREEN_HEIGHT = screen_height
        self.MAX_PARTICLES = max_particles
        self.PARTICLE_LIFETIME = particle_lifetime
        self.PARTICLE_SPEED_DECAY = particle_speed_decay
        self.GLITTER_PROBABILITY = glitter_probability
        self.PLAYER_TIMEOUT = player_timeout
        self.PARTICLE_SIZE = particle_size

        self.players = {}  # Store player data by player ID
        self.particles = {
            "positions": np.zeros((self.MAX_PARTICLES, 2)),
            "velocities": np.zeros((self.MAX_PARTICLES, 2)),
            "lifetimes": np.zeros(self.MAX_PARTICLES),
            "start_colors": np.zeros((self.MAX_PARTICLES, 3)),
            "end_colors": np.zeros((self.MAX_PARTICLES, 3)),
        }
        self.active_particles = 0
        self.frame_count = 0
        self.color_schemes = {}  # Color schemes for each player

    def generate_color_scheme(self, player_id):
        """
        Generate a unique color scheme for a given player_id using predefined colors.
        """
        start_color = COLORS[player_id % len(COLORS)]
        end_color = COLORS[(player_id + 1) % len(COLORS)]
        return start_color, end_color

    def update_player_positions(self, player_data):
        """
        Update players with new positions.
        `player_data` should be a dictionary: {player_id: (x, y)}.
        """
        for player_id, new_pos in player_data.items():
            new_pos = np.array(new_pos, dtype=float)
            if player_id in self.players:
                self.players[player_id]["velocity"] = new_pos - self.players[player_id]["position"]
                self.players[player_id]["position"] = new_pos
                self.players[player_id]["last_seen"] = self.frame_count
            else:
                start_color, end_color = self.generate_color_scheme(player_id)
                self.color_schemes[player_id] = {"start": start_color, "end": end_color}
                self.players[player_id] = {
                    "position": new_pos,
                    "velocity": np.array([0, 0], dtype=float),
                    "last_seen": self.frame_count,
                }

    def remove_inactive_players(self):
        """
        Remove players that have not been updated within the timeout period.
        """
        inactive_players = [
            player_id
            for player_id, player in self.players.items()
            if self.frame_count - player["last_seen"] > self.PLAYER_TIMEOUT
        ]
        for player_id in inactive_players:
            del self.players[player_id]
            del self.color_schemes[player_id]

    def emit_particles(self):
        """
        Emit particles for each active player.
        """
        for player_id, player in self.players.items():
            if self.active_particles >= self.MAX_PARTICLES:
                break
            count = min(self.MAX_PARTICLES - self.active_particles, 5)  # Emit up to 5 particles per player
            indices = np.arange(self.active_particles, self.active_particles + count)
            self.particles["positions"][indices] = player["position"]
            random_velocity = np.random.uniform(-1, 1, (count, 2))
            self.particles["velocities"][indices] = player["velocity"] * 0.1 + random_velocity * 0.5
            self.particles["lifetimes"][indices] = self.PARTICLE_LIFETIME
            self.particles["start_colors"][indices] = self.color_schemes[player_id]["start"]
            self.particles["end_colors"][indices] = self.color_schemes[player_id]["end"]
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

        velocities *= self.PARTICLE_SPEED_DECAY
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
            if np.random.random() < self.GLITTER_PROBABILITY:
                color = (255, 255, 255)  # Glitter: Bright white
            else:
                start_color = self.particles["start_colors"][i]
                end_color = self.particles["end_colors"][i]
                fraction = 1 - (self.particles["lifetimes"][i] / self.PARTICLE_LIFETIME)
                color = start_color + (end_color - start_color) * fraction
                color = tuple(map(int, color))  # Convert to tuple of integers

            if 0 <= int(x) < frame.shape[1] and 0 <= int(y) < frame.shape[0]:
                if self.PARTICLE_SIZE > 1:
                    top_left = (int(x) - self.PARTICLE_SIZE // 2, int(y) - self.PARTICLE_SIZE // 2)
                    bottom_right = (int(x) + self.PARTICLE_SIZE // 2, int(y) + self.PARTICLE_SIZE // 2)
                    cv2.rectangle(frame, top_left, bottom_right, color, -1)
                else:
                    frame[int(y), int(x)] = color  # Draw particle as a single pixel
    def get_frame(self, width, height):
        """
        Generate the current particle frame as a NumPy array.
        """
        frame = np.zeros((self.SCREEN_HEIGHT, self.SCREEN_WIDTH, 3), dtype=np.uint8)
        self.draw_particles(frame)
        return cv2.resize(frame, (width, height))

    def update(self):
        """
        Update frame data and emit particles.
        """
        self.frame_count += 1
        self.remove_inactive_players()
        self.emit_particles()
        self.update_particles()