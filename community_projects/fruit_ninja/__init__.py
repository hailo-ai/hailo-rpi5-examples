"""
Fruit Ninja with Pose Estimation

A real-time Fruit Ninja game that uses hand tracking through pose estimation to slice fruits.
The game integrates with Hailo's pose estimation pipeline and runs a separate pygame process
for the game logic.
"""

__version__ = "1.0.0"
__author__ = "Hailo Community"
__description__ = "Pose estimation-based Fruit Ninja game"

from .fruit_ninja_game import user_app_callback_class, app_callback
from .pygame_fruit_ninja import PygameFruitNinja, Fruit, FruitType

__all__ = [
    'user_app_callback_class',
    'app_callback',
    'PygameFruitNinja',
    'Fruit',
    'FruitType'
]