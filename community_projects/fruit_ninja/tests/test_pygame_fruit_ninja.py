import pytest
import unittest
from unittest.mock import Mock, MagicMock, patch
import queue
import math
import time
import sys
import os

# Add the parent directory to the path to import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fruit_ninja.pygame_fruit_ninja import PygameFruitNinja, Fruit, FruitType

class TestFruit(unittest.TestCase):
    """Test cases for the Fruit dataclass."""

    def test_fruit_creation(self):
        """Test creating a fruit object."""
        fruit = Fruit(
            x=100.0, y=200.0, vx=5.0, vy=-10.0,
            fruit_type=FruitType.APPLE, size=30
        )

        self.assertEqual(fruit.x, 100.0)
        self.assertEqual(fruit.y, 200.0)
        self.assertEqual(fruit.vx, 5.0)
        self.assertEqual(fruit.vy, -10.0)
        self.assertEqual(fruit.fruit_type, FruitType.APPLE)
        self.assertEqual(fruit.size, 30)
        self.assertFalse(fruit.sliced)
        self.assertEqual(fruit.creation_time, 0.0)

    def test_fruit_with_defaults(self):
        """Test creating a fruit with default values."""
        fruit = Fruit(
            x=50.0, y=100.0, vx=2.0, vy=-5.0,
            fruit_type=FruitType.BANANA, size=25,
            creation_time=time.time()
        )

        self.assertFalse(fruit.sliced)
        self.assertGreater(fruit.creation_time, 0)


class TestFruitType(unittest.TestCase):
    """Test cases for the FruitType enum."""

    def test_fruit_types(self):
        """Test all fruit types exist."""
        expected_types = ['apple', 'orange', 'banana', 'watermelon', 'strawberry']

        for expected in expected_types:
            # Check that each type exists and has correct value
            fruit_type = FruitType(expected)
            self.assertEqual(fruit_type.value, expected)

    def test_fruit_type_uniqueness(self):
        """Test that all fruit types are unique."""
        values = [ft.value for ft in FruitType]
        self.assertEqual(len(values), len(set(values)))


class TestPygameFruitNinja(unittest.TestCase):
    """Test cases for the PygameFruitNinja class."""

    def setUp(self):
        """Set up test fixtures."""
        self.hand_queue = Mock()
        self.fruit_queue = Mock()
        self.frame_width = 640
        self.frame_height = 480

    @patch('pygame_fruit_ninja.pygame')
    @patch('pygame_fruit_ninja.random')
    @patch('pygame_fruit_ninja.time')
    def test_update_fruits(self, mock_time, mock_random, mock_pygame):
        """Test updating fruit positions."""
        # Mock pygame
        mock_pygame.init.return_value = None
        mock_pygame.display.set_mode.return_value = Mock()
        mock_pygame.display.set_caption.return_value = None
        mock_pygame.time.Clock.return_value = Mock()
        mock_pygame.font.Font.return_value = Mock()

        # Mock time.time() to return a specific value
        mock_time.time.return_value = 100.0

        game = PygameFruitNinja(
            self.hand_queue, self.fruit_queue,
            self.frame_width, self.frame_height
        )

        # Add a fruit manually
        fruit = Fruit(
            x=100.0, y=200.0, vx=2.0, vy=-5.0,
            fruit_type=FruitType.APPLE, size=30,
            creation_time=99.0  # Use a real number, not time.time()
        )
        game.fruits.append(fruit)

        # Update fruits
        game.update_fruits()

        # Verify physics applied (with new gravity value of 0.15)
        self.assertEqual(fruit.x, 102.0)  # x + vx
        self.assertAlmostEqual(fruit.y, 195.15, places=2)  # y + vy + gravity = 200 + (-5) + 0.15 = 195.15
        self.assertEqual(fruit.vy, -4.85)  # vy + gravity = -5 + 0.15 = -4.85

    @patch('pygame_fruit_ninja.pygame')
    @patch('pygame_fruit_ninja.time')
    def test_update_fruits_removes_old(self, mock_time, mock_pygame):
        """Test that old fruits are removed."""
        # Mock pygame
        mock_pygame.init.return_value = None
        mock_pygame.display.set_mode.return_value = Mock()
        mock_pygame.display.set_caption.return_value = None
        mock_pygame.time.Clock.return_value = Mock()
        mock_pygame.font.Font.return_value = Mock()

        # Mock time.time() to return current time
        current_time = 100.0
        mock_time.time.return_value = current_time

        game = PygameFruitNinja(
            self.hand_queue, self.fruit_queue,
            self.frame_width, self.frame_height
        )

        # Add a fruit that falls off screen
        fruit_off_screen = Fruit(
            x=100.0, y=self.frame_height + 200,  # Off screen
            vx=0.0, vy=0.0,
            fruit_type=FruitType.APPLE, size=30,
            creation_time=current_time - 1.0  # Recent, not old
        )
        game.fruits.append(fruit_off_screen)

        # Add an old fruit that doesn't fall off screen
        fruit_old = Fruit(
            x=100.0, y=200.0,  # On screen
            vx=0.0, vy=0.0,
            fruit_type=FruitType.ORANGE, size=30,
            creation_time=current_time - 20.0  # Old
        )
        game.fruits.append(fruit_old)

        game.update_fruits()

        # Verify both fruits were removed (no lives system anymore)
        self.assertEqual(len(game.fruits), 0)

    @patch('pygame_fruit_ninja.pygame')
    @patch('pygame_fruit_ninja.math')
    def test_check_slicing_fruit(self, mock_math, mock_pygame):
        """Test slicing a fruit."""
        # Mock pygame
        mock_pygame.init.return_value = None
        mock_pygame.display.set_mode.return_value = Mock()
        mock_pygame.display.set_caption.return_value = None
        mock_pygame.time.Clock.return_value = Mock()
        mock_pygame.font.Font.return_value = Mock()

        # Mock distance calculation
        mock_math.sqrt.return_value = 30.0  # Within slice distance

        game = PygameFruitNinja(
            self.hand_queue, self.fruit_queue,
            self.frame_width, self.frame_height
        )

        # Add a fruit and hand position
        fruit = Fruit(
            x=100.0, y=200.0, vx=0.0, vy=0.0,
            fruit_type=FruitType.APPLE, size=30,
            creation_time=time.time()
        )
        game.fruits.append(fruit)
        game.hand_positions[1] = (105, 205)  # Close to fruit

        initial_score = game.score
        game.check_slicing()

        # Verify fruit was sliced and score increased
        self.assertTrue(fruit.sliced)
        self.assertEqual(game.score, initial_score + 10)

    @patch('pygame_fruit_ninja.pygame')
    def test_send_fruit_positions(self, mock_pygame):
        """Test sending fruit positions to queue."""
        # Mock pygame
        mock_pygame.init.return_value = None
        mock_pygame.display.set_mode.return_value = Mock()
        mock_pygame.display.set_caption.return_value = None
        mock_pygame.time.Clock.return_value = Mock()
        mock_pygame.font.Font.return_value = Mock()

        game = PygameFruitNinja(
            self.hand_queue, self.fruit_queue,
            self.frame_width, self.frame_height
        )

        # Add a fruit
        fruit = Fruit(
            x=150.0, y=250.0, vx=0.0, vy=0.0,
            fruit_type=FruitType.ORANGE, size=35,
            creation_time=time.time()
        )
        game.fruits.append(fruit)

        game.send_fruit_positions()

        # Verify fruit data was sent
        self.fruit_queue.put_nowait.assert_called_once()
        call_args = self.fruit_queue.put_nowait.call_args[0][0]
        self.assertEqual(call_args['type'], 'orange')
        self.assertEqual(call_args['position'], (150, 250))
        self.assertEqual(call_args['size'], 35)
        self.assertFalse(call_args['sliced'])

    @patch('pygame_fruit_ninja.pygame')
    def test_send_fruit_positions_queue_full(self, mock_pygame):
        """Test handling queue full exception."""
        # Mock pygame
        mock_pygame.init.return_value = None
        mock_pygame.display.set_mode.return_value = Mock()
        mock_pygame.display.set_caption.return_value = None
        mock_pygame.time.Clock.return_value = Mock()
        mock_pygame.font.Font.return_value = Mock()

        # Mock queue full exception
        self.fruit_queue.put_nowait.side_effect = queue.Full()

        game = PygameFruitNinja(
            self.hand_queue, self.fruit_queue,
            self.frame_width, self.frame_height
        )

        # Add a fruit
        fruit = Fruit(
            x=100.0, y=200.0, vx=0.0, vy=0.0,
            fruit_type=FruitType.APPLE, size=30,
            creation_time=time.time()
        )
        game.fruits.append(fruit)

        # Should not raise exception
        game.send_fruit_positions()

    @patch('pygame_fruit_ninja.pygame')
    def test_receive_hand_positions(self, mock_pygame):
        """Test receiving hand positions from queue."""
        # Mock pygame
        mock_pygame.init.return_value = None
        mock_pygame.display.set_mode.return_value = Mock()
        mock_pygame.display.set_caption.return_value = None
        mock_pygame.time.Clock.return_value = Mock()
        mock_pygame.font.Font.return_value = Mock()

        game = PygameFruitNinja(
            self.hand_queue, self.fruit_queue,
            self.frame_width, self.frame_height
        )

        # Mock hand positions in queue
        hand_positions = {1: (100, 200), 2: (300, 400)}
        self.hand_queue.get_nowait.side_effect = [hand_positions, queue.Empty()]

        game.receive_hand_positions()

        # Verify hand positions were received
        self.assertEqual(game.hand_positions, hand_positions)

    @patch('pygame_fruit_ninja.pygame')
    def test_receive_hand_positions_empty_queue(self, mock_pygame):
        """Test handling empty queue."""
        # Mock pygame
        mock_pygame.init.return_value = None
        mock_pygame.display.set_mode.return_value = Mock()
        mock_pygame.display.set_caption.return_value = None
        mock_pygame.time.Clock.return_value = Mock()
        mock_pygame.font.Font.return_value = Mock()

        # Mock empty queue
        self.hand_queue.get_nowait.side_effect = queue.Empty()

        game = PygameFruitNinja(
            self.hand_queue, self.fruit_queue,
            self.frame_width, self.frame_height
        )

        # Should not raise exception
        game.receive_hand_positions()
        self.assertEqual(len(game.hand_positions), 0)


class TestGameConstants(unittest.TestCase):
    """Test game constants and configuration."""

    def test_fruit_colors(self):
        """Test that all fruit types have colors defined."""
        for fruit_type in FruitType:
            self.assertIn(fruit_type, PygameFruitNinja.FRUIT_COLORS)
            color = PygameFruitNinja.FRUIT_COLORS[fruit_type]
            self.assertEqual(len(color), 3)  # RGB tuple
            for component in color:
                self.assertGreaterEqual(component, 0)
                self.assertLessEqual(component, 255)

    def test_game_constants(self):
        """Test game constants are reasonable."""
        self.assertGreater(PygameFruitNinja.GRAVITY, 0)
        self.assertGreater(PygameFruitNinja.FRUIT_SPAWN_RATE, 0)
        self.assertLess(PygameFruitNinja.FRUIT_SPAWN_RATE, 1)
        self.assertGreater(PygameFruitNinja.SLICE_DISTANCE, 0)
        self.assertGreater(PygameFruitNinja.FRUIT_LIFETIME, 0)


if __name__ == '__main__':
    unittest.main()