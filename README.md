
![Banner](doc/images/hailo_rpi_examples_banner.png)
# Hailo Raspberry Pi 5 examples
Welcome to the Hailo Raspberry Pi 5 Examples repository. This project showcases various examples demonstrating the capabilities of the Hailo AI processor on a Raspberry Pi 5. These examples will help you get started with AI on embedded devices.

## Table of Contents
- [Hailo Raspberry Pi 5 examples](#hailo-raspberry-pi-5-examples)
  - [Table of Contents](#table-of-contents)
  - [Pre-requisites](#pre-requisites)
    - [Hailo Packages Installation](#hailo-packages-installation)
    - [Environment Configuration](#environment-configuration)
    - [Requirements Installation](#requirements-installation)
    - [Resources Download](#resources-download)
  - [Running the Examples](#running-the-examples)
    - [Detection Example](#detection-example)
    - [Pose Estimation Example](#pose-estimation-example)
    - [Instance Segmentation Example](#instance-segmentation-example)
  - [Contributing](#contributing)
  - [License](#license)
  - [Disclaimer](#disclaimer)

![Raspberry Pi 5 with Hailo M.2](doc/images/Raspberry_Pi_5_Hailo-8.png)

## Pre-requisites
You should have Hailo's driver and software installed on your Raspberry Pi 5. Hailo TAPPAS installation is required for running the examples.

### Hailo Packages Installation
For installation instructions, see [Hailo Raspberry Pi 5 installation guide](doc/install-raspberry-pi5.md).

### Environment Configuration
To run the examples, you should ensure your environment is set up correctly. We use the hailo-tappas-core pkgconfig file to get Hailo dependencies.

You can set it all up by sourcing the following script. This script will set the required environment variables and activate the Hailo virtual environment (if it doesn't exist, it will create it).
```bash
source setup_env.sh
```

### Requirements Installation
Make sure you are in the virtual environment and run the following command:
```bash
pip install -r requirements.txt
```

### Resources Download
```bash
./download_resources.sh
```

## Running the Examples

### Detection Example
![Banner](doc/images/detection.gif)
This example demonstrates object detection. As Default it uses YOLOv6n model.
To run the example use:
```bash
python basic_pipelines/detection.py --input resources/detection0.mp4
```
For more details about the detection example, see the [detection example documentation](doc/basic-pipelines.md#detection-example).

### Pose Estimation Example
![Banner](doc/images/pose_estimation.gif)
This example demonstrates human pose estimation. It uses yolov8s_pose model.
To run the example use:
```bash
python basic_pipelines/pose_estimation.py --input resources/detection0.mp4
```
For more details about the pose estimation example, see the [pose estimation example documentation](doc/basic-pipelines.md#pose-estimation-example).

### Instance Segmentation Example
![Banner](doc/images/instance_segmentation.gif)
This example demonstrates instance segmentation. It uses yolov5n_seg model.
To run the example use:
```bash
python basic_pipelines/instance_segmentation.py --input resources/detection0.mp4
```
For more details about the instance segmentation example, see the [instance segmentation example documentation](doc/basic-pipelines.md#instance-segmentation-example).

## Contributing
We welcome contributions from the community.
For now, you can contribute by:
1. Opening a pull request.
2. Reporting issues and bugs.
3. Suggesting new features or improvements.
4. Joining the discussion on the [Hailo Community Forum](https://community.hailo.ai/).

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Disclaimer
This code example is provided by Hailo solely on an “AS IS” basis and “with all faults”. No responsibility or liability is accepted or shall be imposed upon Hailo regarding the accuracy, merchantability, completeness or suitability of the code example. Hailo shall not have any liability or responsibility for errors or omissions in, or any business decisions made by you in reliance on this code example or any part of it. If an error occurs when running this example, please open a ticket in the "Issues" tab.
