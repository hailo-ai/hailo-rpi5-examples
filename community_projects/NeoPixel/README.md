# Hailo NeoPixel exampe
This exmaple is based on the detection pipeline. It detects a person and follows him with the leds.

## Installation
Follow the installation flow in the main README file, and then continue folowing this README file.

### Enable SPI
```bash
sudo raspi-config
```

- 3 Interface Options
- I4 SPI
- Yes
- reboot

### Pins Connection
Based on https://github.com/vanshksingh/Pi5Neo
- Connect 5+ to 5V
- GND to GND
- Din to GPIO10 (SPI MOSI)

### Navigate to the repository directory:
```bash
cd hailo-rpi5-examples
```

### Environment Configuration  (Required for Each New Terminal Session)
Ensure your environment is set up correctly by sourcing the provided script. This script sets the required environment variables and activates the Hailo virtual environment. If the virtual environment does not exist, it will be created automatically.
```bash
source setup_env.sh
```
### Navigate to the example directory:
```bash
cd community_projects/NeoPixel/
```
### Requirements Installation
Within the activated virtual environment, install the necessary Python packages:
```bash
pip install -r requirements.txt
```

### To Run the Simple Example:
```bash
python example.py
```
### To Run the Real Example:
```bash
python follow_detection.py
```
- To close the application, press `Ctrl+C`.
