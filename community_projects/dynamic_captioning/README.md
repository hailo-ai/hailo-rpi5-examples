![](../../resources/Hackathon-banner-2024.png)

# Dynamic Captioning

## Dinamically generate captions of a scene, only when a change in scene occurs. running on Raspberry pi 5 AI kit (powered by Hailo)

[![Watch the video](https://img.youtube.com/vi/nhMLRAJMgh0/0.jpg)](https://youtube.com/shorts/nhMLRAJMgh0?feature=share)

## Requirements

- Raspberry Pi 5 AI kit
- Hailo-8™ AI Processor
- Camera module compatible with Raspberry Pi
- Python 3.7 or higher
- TensorFlow
- Internet connection for downloading models and updates
- Speaker with bluetooth connection


## Installation

- Install espeak:
  ```bash
  sudo apt-get install espeak
  ```
- Install python packages:
    ```bash
    pip install -r requirements.txt
    ```
- Download resources:
    ```bash
    ./download_resources.sh
    ```

- Run app:
    ```bash
    python caption.py 
    ```

- Run app without a speaker:
    ```bash
    python caption.py --no-speaker 
    ```

    
