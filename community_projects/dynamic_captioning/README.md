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


## Installation
- Download the netwrok files (hef files):
    [https://drive.google.com/file/d/1LwLOrzULS-vFsSL0t594If9X2u8ti9Uy/view?usp=sharing](https://drive.google.com/file/d/1mSsYDghBCSIuLYJRrWTW8p1HavO7UPWW/view?usp=sharing)

- Install espeak:
  ```bash
  sudo apt-get install espeak
  ```
- Install python packages:
    ```bash
    pip install -r requirements.txt
    ```
- Run app:
    ```bash
    python caption.py
    ```

    
