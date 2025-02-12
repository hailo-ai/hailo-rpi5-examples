![](../../resources/Hackathon-banner-2024.png)

# TAILO - The Smart Companion for Your Dog

![TAILO_logo_sm](https://github.com/user-attachments/assets/49dd031c-6538-48e3-9aa8-d09c8ff93dc2)

## Overview 
TAILO is a cutting-edge AI-powered device designed to enhance the lives of pets and their owners. By combining advanced artificial intelligence with playful and practical features, TAILO ensures your dog stays happy, active, and monitored while you’re away. Whether it’s reinforcing good behavior, tracking daily activities, or providing interactive play, TAILO is the ultimate companion for your furry friend.

## Video
Here's a video submitted by TAILO's team at the HAILO 2024 MAD Hackathon

[![Watch the demo on YouTube](https://img.youtube.com/vi/dAok4_63W8E/0.jpg)](https://youtu.be/dAok4_63W8E)


## Key Features

### 1. Reinforcement with Treats
- **Behavioral Reinforcement:** Dispense treats to reward pre-defined specific activities or good behavior, promoting a well-trained and happy dog.
  
### 2. Customized Voice Commands
- **Action-Based Prompts:** Configure personalized voice commands to play when specific actions are detected, such as encouraging your dog to sit, stay, or leave restricted areas.

### 3. Pet Tracking
- **Smart Camera Functionality:** Follows your dog’s movement and activities in defined areas. This allows focused tracking, such as observing time spent on the couch, near the door, or in a designated play zone.
---

## Why TAILO?

- **Low Cost of Ownership:** Enjoy the benefits of TAILO without any monthly subscription fees.
- **Connectivity:** Always operational, independent of internet connectivity.
- **Privacy First:** Operates in a closed circle with no data transmitted to the cloud, ensuring your privacy.
- **Customizable:** TAILO is built for Makers. It allows users to define actionable events with free text, tailoring the experience to your needs.
  
---

## Who Is TAILO For?

- **Busy Pet Owners:** Perfect for those who want to ensure their dog is happy and engaged while they’re at work or away.
- **Training Enthusiasts:** Ideal for reinforcing positive behavior and maintaining a structured training routine.
- **Data-Driven Pet Parents:** Provides valuable insights into your dog’s habits and activities.

## Pet State
- PET_HOMING - Pet is not in the frame.
- PET_NOT_CENTERED - Pet is in the frame, but not centered.
- PET_ON_COUCH - Pet is sitting on the couch
- PET_LOCKED - The camera is following the pet

## Setup Instructions
Enable Serial Port for the [Servo SG90](http://www.ee.ic.ac.uk/pcheung/teaching/DE1_EE/stores/sg90_datasheet.pdf) of the cannon.
For the camera angular movment we are using [XL-320](https://emanual.robotis.com/docs/en/dxl/x/xl320/).  
For the 3D printed module to hold the camera we used [Poppy-Project](https://github.com/poppy-project/poppy-ergo-jr).  
For the camera we used the rpi camera module v2.
For the pet warnings we used a bluetooth speaker.
And of course for the AI we used the [Hailo AI HAT](https://www.raspberrypi.com/products/ai-hat/).  
### Schematics
Raspberry pi GPIOs connections:  
GPIO 14 - UART TX connected to Robotics XR-320 servo motor.    
GPIO 15 - UART RX connected to Robotics XR-320 servo motor.  
GPIO 18 - PWM to trigger the treat launching with the SG90 servo.  

### Installation
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
cd community_projects/TAILO/
```
### Requirements Installation
Within the activated virtual environment, install the necessary Python packages:
```bash
pip install -r requirements.txt
./download_resources.sh
```

## Usage
```bash
cd community_projects/TAILO
python main.py -i resources/brandy_on_couch.mp4
```
- To close the application, press `Ctrl+C`.

For those who don't want to use camera angular movment:
```bash
cd community_projects/TAILO
python main.py --no-arm-control -i resources/brandy_on_couch.mp4
```
- To close the application, press `Ctrl+C`.

To run from rpi camera:
```bash
cd community_projects/TAILO
python main.py  -i rpi
```
- To close the application, press `Ctrl+C`.


## Change Pet Warnings and Treats:
Replace the files under community_projects/TAILO/resources/ folder.
