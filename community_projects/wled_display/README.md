# WLED Display
## Overview
This project provides a Python interface for controlling WLED-based LED matrix displays, with specific integration for Hailo AI pipelines. It enables real-time visualization of AI processing results on LED matrices, making it perfect for interactive AI demonstrations and visual feedback systems.
WLED is an awesome open source project for controlling LEDS.
For more information see the [WLED documentation page](https://kno.wled.ge/).

## Features
- Real-time LED matrix control via UDP protocol
- Multi-panel support
- Integration with Hailo AI pipelines
- Debug visualization window
- Process-based frame handling
- Multiple example applications
- Gesture-based interactive applications

## Prerequisites
- WLED-compatible LED matrix
- Hailo AI accelerator (for AI-based examples)

## Installation
1. Set up the hailo-rpi5-examples project and enter its virtual environment.

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## WLEDDisplay Class
The `WLEDDisplay` class (`wled_display.py`) is the core component for LED matrix control.

### Key Features
- UDP-based WLED communication
- Multi-process frame handling
- Real-time debug visualization
- Support for multiple panels
- Configurable display dimensions
- Built-in debug patterns

### Basic Usage
```python
from wled_display import WLEDDisplay

# Initialize display
wled = WLEDDisplay(
    ip="192.168.1.100",  # WLED device IP
    panel_width=20,      # Width in pixels
    panel_height=20,     # Height in pixels
    panels=1,            # Number of panels
    wled_enabled=True    # Enable WLED output
)

# Send a frame
frame = your_frame_data  # numpy array (height, width, 3)
wled.frame_queue.put(frame)
```

## Example Applications

### 1. Instance Segmentation Visualizer
```bash
python wled_segmentation.py
```
Demonstrates real-time instance segmentation with unique colors for each detected person.

### 2. Basic Pose Estimation Display
```bash
python wled_pose_estimation.py
```
Visualizes detected hand positions from pose estimation pipeline.

### 3. Gesture Drawing Board
```bash
python gesture_drawing_app.py
```
Advanced interactive application featuring:
- Right-hand drawing control
- Left-hand write mode activation
- Color palette selection
- T-pose canvas reset gesture
- Real-time gesture recognition

### 4. Particle-Based Pose Visualization
```bash
python wled_pose_estimation_particles.py
```
Advanced example demonstrating:
- External process integration
- Particle animation system
- Real-time pose data visualization

## Configuration
The WLEDDisplay class accepts the following parameters:
- `ip`: WLED device IP or hostname
- `port`: UDP port (default: 21324)
- `panel_width`: Panel width in pixels
- `panel_height`: Panel height in pixels
- `panels`: Number of connected panels
- `wled_enabled`: Toggle WLED output

## Hardware Setup
The project requires:
- Hailo AI accelerator
- Camera (for AI-based examples)
- WLED-compatible LED matrix (optional)
- ESP32 controller (optional)

The LED panel I used is [Smart Curtain Lights 6.6x6.6Ft, 400 LED Curtain Light APP Remote Control Music Sync Dynamic DIY Lights for Bedroom Wall Backdrop Easter Christmas Decor](https://a.co/d/bHCMbWR)
Item model number DMO-400

Probably any LED panel which supports the WLED firmware will work. Make sure your LED panel uses WE281x LEDs. This protocol uses 3 wires:
- 5V
- GND
- Data

Other protocols supported by WLED should work as well, but I have not tested them and you will have to figure out the correct parameters and wiring.

### WLED controller:
I used an ESP32 controller to run the WLED firmware.
The controller is connected to the LED panel via a 3-wire protocol. You can probably use an ESP8266 controller as well if you don't need to control so many LEDs (Note that the ESP8266 support will be discontinued).
The controller is programmed to run the WLED firmware and is controlled via a web interface. To install the WLED firmware on the ESP32 controller see the [WLED getting started guide](https://kno.wled.ge/basics/getting-started/).
The simple way to install the WLED firmware on the ESP32 controller is to use the [WLED web installer](https://install.wled.me/).

### Wiring:
Before you start hacking away make sure that the LED panel is working using the supplied application. I bought 3 and one of them was defective. Asking for a replacement was not an option after cutting the original controller ;)

In the model I used the 5V and GND wires are the external ones and the data line is in the middle. The 5V wire is marked with black dots. If you are not sure or have a different model you can use a multimeter to find the correct wires. Note that the data wire carrying a control signal and should read ~0.1V when the LED panel is working. Don't mix it with the GND wire.

The LEDS should be powered by a 5V supply. Running from a laptop USB port might not be enough. I used a 5V 4A power supply. I have a separate connection from the power supply to the ESP32 controller. This way I can power the LEDS from the power supply and the controller from the laptop USB port while debugging. In the final solution the 5V supply is powering the ESP32 as well.


*Detailed hardware setup guide coming soon...*

## Debugging
- Real-time preview window available
- Built-in debug pattern generator
- Frame rate monitoring
- Connection status checking

## Performance Considerations
- Uses UDP for efficient data transmission
- Multi-process architecture for smooth operation
- Automatic chunking for large LED arrays
- Configurable frame rates

## Contributing
Contributions are welcome! Please feel free to submit pull requests or open issues for:
- New features
- Bug fixes
- Documentation improvements
- Example applications

## Troubleshooting
Common issues and solutions:
1. Connection issues:
   - Verify WLED device IP address
   - Check network connectivity
   - Ensure WLED firmware version compatibility

2. Display problems:
   - Verify panel dimensions
   - Check UDP port settings
   - Monitor system resources



## Acknowledgments
- WLED project (https://github.com/Aircoookie/WLED)
- Hailo Technologies