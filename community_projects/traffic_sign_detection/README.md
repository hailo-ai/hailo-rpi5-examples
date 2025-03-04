## Overview
This application demonstrates a Traffic Sign Detection & mapping application with GPS coordinates. The application performs the following steps:
1. Object detection using the YOLO network.
2. If a stop sign is detected, the GPS coordinates are recorded.
* Currently, only stop signs are supported.
The ouput is a csv file and then should be passed via "post_process_csv.py" python code to get the final result in csv and GeoJSON file.

## Versions
The application has been verified with the following versions:
- HailoRT Version: 4.20.0
- TAPPAS: 3.31.0

## Setup Instructions
1. Pre-requisite: Ensure that [hailo-apps-infra](https://github.com/hailo-ai/hailo-apps-infra) is installed. This requirement should already be met as part of the current ("hailo-rpi-examples") installation dependencies.
2. A GPS sensor is connected to Pi. The app was tested with L76X Multi-GNSS HAT for Raspberry Pi connected via USB and mode pins set to A+B.
3. Navigate to the hailo-rpi5-examples directory:
   ```bash
   cd hailo-rpi5-examples
   ```
4. Activate the virtual environment:
   ```bash
   source setup_env.sh
   ```
   If using a remote VNC connection or similar to Pi, additionally run:
   ```bash
   export DISPLAY=:0
   ```
5. Navigate to the current project directory:
   ```bash
   cd community_projects/traffic_sign_detection
   ```
6. Ensure the install.sh file is executable:
   ```bash
   chmod +x install.sh
   ```
7. Execute the install.sh: This will download required Python packages as listed in requirements.txt
   ```bash
   ./install.sh
   ```

## Usage
Examples of how to run the script:
1. Run the application with the following command:
   ```bash
   python app.py --input rpi
   ```
2. The mapping results will be written to a CSV file named `tsr_mapping.csv`, with columns ['id', 'latitude', 'longitude', 'altitude'].
3. The last reading for each id is the final mapping result. Please see the post-processing example in the "post_process_csv.py" file - the code can be executed simply by typing from current project directory:
   ```bash
   python post_process_csv.py
   ```