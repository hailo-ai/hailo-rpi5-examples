import pygame
import random
import math
import time
import queue
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum


class FruitType(Enum):
    """Enumeration of different fruit types."""
    APPLE = "apple"
    ORANGE = "orange"
    BANANA = "banana"
    WATERMELON = "watermelon"
    STRAWBERRY = "strawberry"


@dataclass
class Fruit:
    """
    Represents a fruit object in the game.

    Attributes:
        x (float): X position
        y (float): Y position
        vx (float): X velocity
        vy (float): Y velocity
        fruit_type (FruitType): Type of fruit
        size (int): Size of the fruit (current, may grow during explosion)
        sliced (bool): Whether the fruit has been sliced
        creation_time (float): Time when fruit was created
        exploding (bool): Whether the fruit is in explosion animation
        explosion_start_frame (Optional[int]): Frame number when explosion started
        class_id (int): Class ID for coloring bounding box
    """
    x: float
    y: float
    vx: float
    vy: float
    fruit_type: FruitType
    size: int
    sliced: bool = False
    creation_time: float = 0.0
    exploding: bool = False
    explosion_start_frame: Optional[int] = None
    class_id: int = 0


class PygameFruitNinja:
    """
    Pygame-based Fruit Ninja game that runs in a separate process.

    Communicates with the main pose estimation process via queues.
    """

    # === Game Parameters (Tweak here) ===
    GRAVITY = 0.15  # Slower falling
    FRUIT_SPAWN_RATE = 0.015  # Probability per frame
    SLICE_DISTANCE = 40  # Distance threshold for slicing
    FRUIT_LIFETIME = 10.0  # Seconds before fruit disappears

    # Fruit velocity ranges
    FRUIT_VX_RANGE = (-1.5, 1.5)  # Horizontal velocity
    FRUIT_VY_RANGE = (-15, -8)    # Vertical velocity (upwards)
    FRUIT_SIZE_RANGE = (40, 60)

    # Explosion animation
    EXPLOSION_FRAMES = 15
    EXPLOSION_GROWTH_PER_FRAME = 1.04  # 4% growth per frame

    # Fruit colors (RGB)
    FRUIT_COLORS = {
        FruitType.APPLE: (255, 0, 0),      # Red
        FruitType.ORANGE: (255, 165, 0),   # Orange
        FruitType.BANANA: (255, 255, 0),   # Yellow
        FruitType.WATERMELON: (0, 255, 0), # Green
        FruitType.STRAWBERRY: (255, 20, 147), # Deep pink
    }

    # Mapping from FruitType to class_id
    FRUIT_CLASS_IDS = {
        FruitType.APPLE: 1,
        FruitType.ORANGE: 6,
        FruitType.BANANA: 3,
        FruitType.WATERMELON: 9,
        FruitType.STRAWBERRY: 0,
    }

    def __init__(self, hand_positions_queue: queue.Queue, fruits_queue: queue.Queue,
                 frame_width: int, frame_height: int):
        """
        Initialize the Fruit Ninja game.

        Args:
            hand_positions_queue: Queue to receive hand positions from pose estimation
            fruits_queue: Queue to send fruit positions back to main process
            frame_width: Width of the video frame
            frame_height: Height of the video frame
        """
        self.hand_positions_queue = hand_positions_queue
        self.fruits_queue = fruits_queue
        self.frame_width = frame_width
        self.frame_height = frame_height

        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((frame_width, frame_height))
        pygame.display.set_caption("Fruit Ninja - Hand Tracking")
        self.clock = pygame.time.Clock()

        # Game state
        self.fruits: List[Fruit] = []
        self.hand_positions: Dict[int, Tuple[int, int]] = {}
        self.score = 0
        self.running = True

        # Font for UI
        self.font = pygame.font.Font(None, 36)

        self.frame_count = 0  # Add frame counter for explosion timing

        print("Pygame Fruit Ninja initialized")

    def spawn_fruit(self) -> None:
        """Spawn a new fruit at the bottom of the screen."""
        # Random spawn position at bottom
        x = random.randint(50, self.frame_width - 50)
        y = self.frame_height + 50

        # Random upward velocity - slower horizontal, higher vertical
        vx = random.uniform(*self.FRUIT_VX_RANGE)
        vy = random.uniform(*self.FRUIT_VY_RANGE)

        # Always choose a regular fruit
        fruit_type = random.choice([
            FruitType.APPLE, FruitType.ORANGE, FruitType.BANANA,
            FruitType.WATERMELON, FruitType.STRAWBERRY
        ])
        size = random.randint(*self.FRUIT_SIZE_RANGE)

        fruit = Fruit(
            x=x, y=y, vx=vx, vy=vy,
            fruit_type=fruit_type, size=size,
            creation_time=time.time(),
            class_id=self.FRUIT_CLASS_IDS[fruit_type]
        )
        self.fruits.append(fruit)

    def update_fruits(self) -> None:
        """Update fruit positions and physics, and handle explosion animation."""
        current_time = time.time()
        fruits_to_remove = []
        for fruit in self.fruits:
            if fruit.exploding:
                if fruit.explosion_start_frame is None:
                    fruit.explosion_start_frame = self.frame_count
                    fruit._original_size = fruit.size  # Store original size for growth
                frames_elapsed = self.frame_count - fruit.explosion_start_frame
                fruit.size = int(fruit._original_size * (self.EXPLOSION_GROWTH_PER_FRAME ** frames_elapsed))
                if frames_elapsed >= self.EXPLOSION_FRAMES:
                    fruits_to_remove.append(fruit)
                continue  # Do not update position if exploding

            # Apply gravity
            fruit.vy += self.GRAVITY

            # Update position
            fruit.x += fruit.vx
            fruit.y += fruit.vy

            # Remove fruits that are off-screen or too old
            if (fruit.y > self.frame_height + 100 or
                current_time - fruit.creation_time > self.FRUIT_LIFETIME):
                fruits_to_remove.append(fruit)

        # Remove old fruits
        for fruit in fruits_to_remove:
            self.fruits.remove(fruit)
        self.frame_count += 1  # Increment frame counter

    def check_slicing(self) -> None:
        """Check if any fruits are sliced by hand positions."""
        for hand_id, (hand_x, hand_y) in self.hand_positions.items():
            for fruit in self.fruits:
                if fruit.sliced:
                    continue

                # Calculate distance between hand and fruit
                distance = math.sqrt((hand_x - fruit.x)**2 + (hand_y - fruit.y)**2)

                if distance < self.SLICE_DISTANCE:
                    fruit.sliced = True
                    fruit.exploding = True
                    # Sliced fruit - gain points
                    self.score += 10
                    print(f"Fruit sliced! Score: {self.score}")

    def send_fruit_positions(self) -> None:
        """Send current fruit positions to the main process."""
        try:
            for fruit in self.fruits:
                fruit_data = {
                    'type': fruit.fruit_type.value,
                    'position': (int(fruit.x), int(fruit.y)),
                    'size': fruit.size,
                    'sliced': fruit.sliced,
                    'exploding': fruit.exploding,
                    'class_id': fruit.class_id
                }
                self.fruits_queue.put_nowait(fruit_data)
        except queue.Full:
            pass  # Skip if queue is full

    def receive_hand_positions(self) -> None:
        """Receive hand positions from the main process."""
        try:
            while True:
                hand_positions = self.hand_positions_queue.get_nowait()
                self.hand_positions = hand_positions
        except queue.Empty:
            pass  # No new hand positions

    def draw(self) -> None:
        """Draw the game state."""
        # Clear screen
        self.screen.fill((0, 0, 0))  # Black background

        # Draw fruits and explosions
        for fruit in self.fruits:
            if fruit.exploding:
                explosion_color = (255, 255, 128)  # Yellowish for fruit
                pygame.draw.circle(
                    self.screen,
                    explosion_color,
                    (int(fruit.x), int(fruit.y)),
                    fruit.size,
                    width=4
                )
                continue  # Skip drawing the fruit itself

            color = self.FRUIT_COLORS[fruit.fruit_type]

            # Make sliced fruits semi-transparent
            if fruit.sliced:
                # Create a surface with alpha for transparency
                fruit_surface = pygame.Surface((fruit.size * 2, fruit.size * 2), pygame.SRCALPHA)
                pygame.draw.circle(fruit_surface, (*color, 128), (fruit.size, fruit.size), fruit.size)
                self.screen.blit(fruit_surface, (fruit.x - fruit.size, fruit.y - fruit.size))
            else:
                pygame.draw.circle(self.screen, color, (int(fruit.x), int(fruit.y)), fruit.size)

        # Draw hand positions
        for hand_id, (hand_x, hand_y) in self.hand_positions.items():
            pygame.draw.circle(self.screen, (255, 255, 255), (hand_x, hand_y), 10)
            pygame.draw.circle(self.screen, (0, 255, 255), (hand_x, hand_y), 5)

        # Draw UI
        score_text = self.font.render(f"Score: {self.score}", True, (255, 255, 255))

        self.screen.blit(score_text, (10, 10))

        pygame.display.flip()

    def run(self) -> None:
        """Main game loop."""
        print("Starting Fruit Ninja game loop...")

        while self.running:
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # Receive hand positions from pose estimation
            self.receive_hand_positions()

            # Spawn new fruits randomly
            if random.random() < self.FRUIT_SPAWN_RATE:
                self.spawn_fruit()

            # Update game state
            self.update_fruits()
            self.check_slicing()

            # Send fruit positions to main process
            self.send_fruit_positions()

            # Draw everything
            self.draw()

            # Control frame rate
            self.clock.tick(60)  # 60 FPS

        print(f"Game ended. Final score: {self.score}")
        pygame.quit()

    @staticmethod
    def run_game(hand_positions_queue: queue.Queue, fruits_queue: queue.Queue,
                 frame_width: int, frame_height: int) -> None:
        """
        Run the Fruit Ninja game in a separate process.

        This static method is intended to be used as the target for a multiprocessing.Process.
        It initializes the game and enters the main game loop.

        Args:
            hand_positions_queue (queue.Queue): Queue to receive hand positions
            fruits_queue (queue.Queue): Queue to send fruit positions
            frame_width (int): Width of the video frame
            frame_height (int): Height of the video frame
        """
        try:
            game = PygameFruitNinja(hand_positions_queue, fruits_queue, frame_width, frame_height)
            game.run()
        except Exception as e:
            print(f"Error in pygame process: {e}")
        finally:
            try:
                pygame.quit()
            except:
                pass


if __name__ == "__main__":
    # Test the game standalone
    import multiprocessing as mp

    hand_queue = mp.Queue()
    fruit_queue = mp.Queue()

    game = PygameFruitNinja(hand_queue, fruit_queue, 640, 480)
    game.run()