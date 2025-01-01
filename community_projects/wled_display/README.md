# WLED Display
## Overview
This project allows to control a WLED panel using Python.
The examples include integration with Hailo pipelines to control the output.

## Versions
This was tested with version 4.19

## Setup Instructions
Make sure you run the project setup i.e. source setup_env.sh
Run the following commands:
```bash
pip install -r requirements.txt
```

## Usage
To run the examples, run the following commands.
These examples are using the Hailo apps infrastructure pipelines so all of its features are available. Try adding `--help` to see the available options.

### Instance Segmentation example:
This example uses the Hailo pipeline to perform instance segmentation. Each person is segmented and displayed on the WLED panel with a different color.
```bash
python wled_segmentation.py
```

### Pose Estimation example (simple):
This example uses the Hailo pipeline to perform pose estimation. The hand positions of the persons detected are displayed on the WLED panel.

```bash
python wled_pose_estimation.py
```
### Pose Estimation drawing board example (advanced):
This advanced example uses the Hailo pipeline to perform pose estimation and allows users to draw on a WLED panel using hand gestures.

Features
Right Hand Drawing: The right hand is used for drawing on the WLED panel.
Write Mode Activation: The left hand, when held by the chest, activates the "write mode" allowing the right hand to draw.
Color Palette: A vertical color palette on the right side of the LED matrix allows users to change drawing colors using their right wrist.
T-Pose Detection: Detects a T-pose gesture to reset the drawing canvas after holding the pose for a specified duration.

```bash
python gesture_drawing_app.py
```


### Pose Estimation example (advanced):
In this example, the hand positions of the persons detected are sent to an external process that implements particle animation. This is an example to send the AI output to an external process.
The external process is implemented in the file [particle_simulation.py](particle_simulation.py).
```bash
python wled_pose_estimation_particles.py
```

## WLEDDisplay class:
The class WLEDDisplay is used to control the WLED panel.
It is defined in the file [wled_display.py](wled_display.py).

### Features
UDP Communication: Sends LED data to WLED panels over UDP.
Frame Queue: Use a multiprocessing queue to handle frames.
Debug Display: Show the current frame in a debug window.
Debug Pattern: Generate a debug pattern for testing.

# Hardware Setup
Guide for building the project HW will be added soon....