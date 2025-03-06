## Overview
This application demonstrates a cascading TAPPAS pipeline using the Hailo cropper pipeline element. The pipeline performs the following steps:
1. Object detection using the YOLO network.
2. If a person is detected, the bounding box of the detected person is cropped.
3. The cropped bounding box is sent to a depth estimation network.

The depth estimation is relative, meaning the values indicate which points are closer or further away without units of measurement. The application supports scdepthv3 relative depth network: [scdepthv3](https://arxiv.org/abs/2211.03660).

Additionally, the application demonstrates modifying cropper script, used to control the way the hailocropper crop the detection in C++. Similar mechanism is typically used for native C++ post processing in pipelines. Users are required to compile the C++ code, thereby familiarizing themselves with the full cycle of post-processing options.

## Versions
The application has been verified with the following versions:
- HailoRT Version: 4.20.0
- TAPPAS: 3.31.0

## Setup Instructions
1. Pre-requisite: Ensure that [hailo-apps-infra](https://github.com/hailo-ai/hailo-apps-infra) is installed. This requirement should already be met as part of the current ("hailo-rpi-examples") installation dependencies.
2. Navigate to the hailo-rpi5-examples directory:
   ```bash
   cd hailo-rpi5-examples
   ```
3. Activate the virtual environment:
   ```bash
   source setup_env.sh
   ```
   If using a remote VNC connection or similar to Pi, additionally run:
   ```bash
   export DISPLAY=:0
   ```
4. Navigate to the current project directory:
   ```bash
   cd community_projects/detection_cropper
   ```
5. Ensure the compile_postprocess.sh file is executable:
   ```bash
   chmod +x compile_postprocess.sh
   ```
6. Compile the C++ post-processing:
   ```bash
   ./compile_postprocess.sh
   ```

## Usage
Examples of how to run the script: Run the application with the following command:
```bash
python app.py --input rpi --apps_infra_path "<path_to_hailo_apps_infra>"
```
