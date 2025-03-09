# Hailo Games | Sailted Fish

<img src="https://i.ibb.co/tp3vCYK/image.png" alt="Sailted Fish Logo" width="156" height="100">


## Overview

Sailted Fish 🐟 is a Red Light 🔴 Green Light 🟢 game that uses advanced AI-driven pose estimation to track player movements with yolov_pose. If a player moves during "Red Light," they are flagged as "Salted Fish" 🐟 and eliminated from the round. The last player who stays still through "Red Light" is the winner 🏆.

## Video

[![watch the video](https://img.youtube.com/vi/q8ZG8zzRlzE/hqdefault.jpg)](https://youtube.com/shorts/q8ZG8zzRlzE)

## Versions

🛠️ Tested and verified on:

- Python 3.11
- GTK 3.0
- GStreamer 1.0
- Raspberry Pi 5

## Setup Instructions

📦 To set up Sailted Fish, follow these steps:

Install the required dependencies:

1.
   ```bash
   pip install -r requirements.txt
   ```
2.
   ```bash
   sudo apt-get install espeak espeak-ng
   ```


## Features

- ✋ Touch Screen: Intuitive controls with touch screen integration for an enhanced experience.
- 🕹️ **GUI:** Easy-to-use interface for start, stop, and choose gameplay levels.
- 🎵 **Music & Sounds:** Enjoy background music and sound effects during gameplay.
- 🧐 **AI Pose Estimation:** Tracks player movements accurately with Hailo App.

## Usage

Open the GUI:

```bash
python start_gui.py
```
<img src="https://i.ibb.co/qRGj2Wt/saited-fish-gui.jpg" alt="gui" width="484" height="400">

🚀 You can customize the gameplay difficulty levels:

- `easy`
- `medium`
- `hard`

Stop the game by clicking the "Stop" button.\
You can change the level after you stop the game.

## License

📜 Sailted Fish is licensed under the MIT License. See the LICENSE file for full details.

