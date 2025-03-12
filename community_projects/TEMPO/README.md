![](../../resources/Hackathon-banner-2024.png)

# TEMPO

Song generation based on heart rate. The code generates music according to your heart rate.

![Pipeline](https://i.imgur.com/VhYneIl.png)

Based on the work of [SkyTNT Midi-Model](https://github.com/SkyTNT/midi-model).

The model we compiled to Hailo is [midi-model-tv2o-medium](https://huggingface.co/skytnt/midi-model-tv2o-medium).

[![VIDEO](https://img.youtube.com/vi/nQr9nL7bH3k/0.jpg)](https://youtu.be/nQr9nL7bH3k)
## Requirements

The packages are described in the requirements (in addition to the requirements of the whole repo).

## Run Options

You can run either with a heart monitor, which will choose the initial BPM in the generation, or by choosing the generation manually.

## Setup

1. Setup virtual environment:
   From the hailo-rpi-example top directory, run:
    ```bash
    . setup_env.sh
    cd community_projects/TEMPO
    pip install -r requirements.txt
    sudo chmod +x download_files.sh
    ./download_files.sh
    ```
2. Hardware Setup (for using heart monitor)

## Hardware Setup - Heart Monitor (Optional)
### Hardware Requirements
- Heart monitor: [Pulse Sensor](https://pulsesensor.com/)
- A2D: part number ADS1115
- Jumpers to connect Raspberry Pi header to the sensor

### Hardware Connections
#### Connect the heart monitor to the analog input A0 of the A2D
- Prepare the sensor according to the [official site](https://cdn.shopify.com/s/files/1/0100/6632/files/PulseSensor_Datasheet_2024-Nov.pdf?v=1732032216)
- Connect the red wire to the 3.3V pin of the A2D
- Connect the black wire to the ground pin of the A2D
- Connect the purple wire to the A0 pin of the A2D

#### Connect the A2D to the Raspberry Pi in the correct GPIO of I2C0
- An image of the pinout is available at [element14 community](https://community.element14.com/products/raspberry-pi/m/files/148385)
- Pin 1 is 3.3V of the A2D
- Pin 3 is SDA
- Pin 5 is SCL
- Pin 6 is Ground

### Put the heart monitor on your finger using the velcro tape provided in your purchase.
The tape should be strong enough to not fall from the finger but not too tight for a reliable read, as the monitor uses the light reflection coming from the veins.

## Running the Program

1. Run the web application (not using heart monitor):
    - Run `python app_hailo.py --port 8080 --batch 1`
    - Open the web browser and go to `http://localhost:8080`
    - After the web UI opens, click "Load Model". This will load the HEF file.
    - Configure your preferences and click "Generate".
    - In this version, you can control all the sliders and options.

2. Run using heart monitor:
    - Run `python app_heart_bit.py`
    - When running with the heart monitor, the music is generated and then played.

## Additional Notes

- On the heart monitor application, BPM measurements are printed for about 20 seconds. You can ignore them as the final result will be calculated over the whole 20 seconds.
- If the heart monitor is not put on correctly, the BPM will be 0 for all measurements, and the program will not work.

## Disclaimer

This code example is provided by Hailo solely on an “AS IS” basis and “with all faults”. No responsibility or liability.
