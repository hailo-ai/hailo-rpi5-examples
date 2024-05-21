
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
  - [Adding Your Own Code](#adding-your-own-code)
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
After setting up the environment (source setup_env.sh), you can run the examples by executing the following commands:
```bash
python hailo_rpi5_examples/detection.py --input resources/detection0.mp4
python hailo_rpi5_examples/pose_estimation.py --input resources/detection0.mp4
python hailo_rpi5_examples/instance_segmentation.py --input resources/detection0.mp4
```

These examples run with a USB camera by default (/dev/video0). You can change the input source using the --input flag. To run with a Raspberry Pi camera, use `--input rpi`. Here are a few examples:
```bash
python hailo_rpi5_examples/detection.py --input /dev/video2
python hailo_rpi5_examples/detection.py --input rpi
python hailo_rpi5_examples/detection.py --input resources/detection0.mp4
```
See the help for more options:
```bash
python hailo_rpi5_examples/detection.py --help
python hailo_rpi5_examples/pose_estimation.py --help
python hailo_rpi5_examples/instance_segmentation.py --help
```

## Adding Your Own Code
You can add your own code to the examples by editing the "app_callback" function in the examples. See the example code for more details. In the examples, you'll also find an "app_callback_class" example to pass user data to the callback function. Each example includes code for parsing the metadata inferred by the network. Note that extracting the video frame and displaying it can slow down the application. The way it is used is not optimized and is shown as a simple example.

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
