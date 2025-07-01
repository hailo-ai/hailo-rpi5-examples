# Fruit Ninja with Pose Estimation

A real-time Fruit Ninja game that uses hand tracking through pose estimation to slice fruits. The game integrates with Hailo's pose estimation pipeline and runs a separate pygame process for the game logic.
We are using "detection" bounding boxes to draw the fruits on the video stream.


## Overview

This application demonstrates:
- **Pose Estimation Integration**: Uses Hailo's pose estimation pipeline to track hand positions
- **Multi-Process Architecture**: Pygame runs in a separate process for optimal performance
- **Real-time Communication**: Hand positions are sent to the game, fruit positions are sent back to the video overlay
- **Hailo Detection Integration**: Fruits appear as detections in the video stream via HailoOverlay

## Features

- **Hand Tracking**: Tracks left and right wrist positions from pose estimation
- **Improved Fruit Physics**: Fruits fly higher and slower for better gameplay experience
- **Multiple Fruit Types**: Apple, Orange, Banana, Watermelon, Strawberry
- **Scoring System**: Gain points for slicing fruits
- **Endless Gameplay**: Game runs continuously without game over
- **Real-time Overlay**: Fruits appear as bounding boxes in the video stream

## Game Mechanics

### Controls
- **Hand Movement**: Move your hands to slice fruits
- **Slicing**: Get your hand close to a fruit to slice it
- **Exit**: Press ESC key or close pygame window to exit

### Scoring
- **+10 points** per fruit sliced
- **Endless gameplay**: Game runs continuously without game over

### Fruit Types
- 🍎 **Apple** (Red)
- 🍊 **Orange** (Orange)
- 🍌 **Banana** (Yellow)
- 🍉 **Watermelon** (Green)
- 🍓 **Strawberry** (Pink)

## Installation

### Prerequisites
- Hailo RPi5 Examples environment set up
- pygame library
- USB camera or RPi camera


### Setup
1. Navigate to the project directory:
   ```bash
   cd community_projects/fruit_ninja
   ```

2. Install pygame if not already installed:
   ```bash
   pip install pygame
   ```

## Usage

### With RPi Camera Input
```bash
python fruit_ninja_game.py --input rpi
```
### With USB Camera Input
```bash
python fruit_ninja_game.py --input usb
```

## Architecture

### Process Structure
```
Main Process (Pose Estimation)
├── GStreamer Pipeline
├── Pose Estimation Model
├── Hand Position Extraction
└── Hailo Detection Injection

Pygame Process (Game Logic)
├── Fruit Physics Simulation
├── Collision Detection
├── Score Management
└── Game Rendering
```

### Communication Flow
1. **Pose Estimation** → Extract hand positions from landmarks
2. **Hand Positions** → Send to pygame via queue
3. **Game Logic** → Process hand positions, update fruits
4. **Fruit Positions** → Send back to main process via queue
5. **Hailo Detections** → Add fruits as detections to video stream
6. **Video Overlay** → HailoOverlay renders fruit bounding boxes

### Key Components

#### `fruit_ninja_game.py`
- Main application entry point
- Integrates with Hailo pose estimation pipeline
- Manages inter-process communication
- Converts fruit positions to Hailo detections

#### `pygame_fruit_ninja.py`
- Pygame-based game implementation
- Handles fruit physics and collision detection
- Manages game state (score, lives, etc.)
- Runs in separate process for performance

### Code Structure
```
fruit_ninja/
├── fruit_ninja_game.py      # Main application
├── pygame_fruit_ninja.py    # Game logic
├── README.md               # This file
└── tests/                  # Unit tests
```

## License

This project is part of the Hailo RPi5 Examples and follows the same MIT license.

## Contributing

1. Follow the existing code style
2. Add docstrings to all functions (the codebase is now fully documented)
3. Test with different input sources
4. Update README for new features

## Game Parameters

All main game parameters can be tuned at the top of `pygame_fruit_ninja.py` in the `PygameFruitNinja` class:

- `GRAVITY`: Controls how fast fruits fall (default: 0.15)
- `FRUIT_SPAWN_RATE`: Probability per frame to spawn a fruit (default: 0.015)
- `SLICE_DISTANCE`: Distance threshold for slicing (default: 40)
- `FRUIT_LIFETIME`: Seconds before fruit disappears (default: 10.0)
- `FRUIT_VX_RANGE`: Horizontal velocity range for fruits (default: -1.5 to 1.5)
- `FRUIT_VY_RANGE`: Vertical velocity range for fruits (default: -15 to -8)
- `FRUIT_SIZE_RANGE`: Size range for fruits (default: 40 to 60)
- `EXPLOSION_FRAMES`: Frames for explosion animation (default: 15)
- `EXPLOSION_GROWTH_PER_FRAME`: Growth factor per explosion frame (default: 1.04)

## Fruit Class IDs

Each fruit is assigned a `class_id` for coloring bounding boxes in overlays:

- Apple: 1
- Orange: 6
- Banana: 3
- Watermelon: 9
- Strawberry: 0

This is included in the data sent from the game to the main process.