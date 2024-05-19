
![Banner](doc/images/hailo_rpi_examples_banner.png)
# hailo_rpi5_examples

This repository contains examples for running Hailo's AI processor on Raspberry Pi 5.

## Table of Contents
- [hailo\_rpi5\_examples](#hailo_rpi5_examples)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Pre-requisites](#pre-requisites)
    - [Hailo TAPPAS core Installation](#hailo-tappas-core-installation)
    - [Configure Environment](#configure-environment)
    - [Install the Required Packages](#install-the-required-packages)
    - [Download the Models (HEF files)](#download-the-models-hef-files)
  - [Running the Examples](#running-the-examples)
  - [Adding Your Own Code](#adding-your-own-code)
  - [Contributing](#contributing)
  - [License](#license)

## Introduction
Welcome to the Hailo Raspberry Pi 5 Examples repository. This project showcases various examples demonstrating the capabilities of the Hailo AI processor on a Raspberry Pi 5. These examples will help you get started with AI on embedded devices.

![Raspberry Pi 5 with Hailo M.2](doc/images/Raspberry_Pi_5_Hailo-8.png)

## Pre-requisites
You should have Hailo's Driver and software installed on your Raspberry Pi 5. Hailo TAPPAS installation is required for running the examples.

### Hailo TAPPAS core Installation
For installation instructions, see [install-raspberry-pi5.md](doc/install-raspberry-pi5.md).

### Configure Environment
To run the examples, you should make sure your environment is set up correctly. We use the hailo-tappas-core pkgconfig file to get Hailo dependencies.

You can set it all up by sourcing the following script:
```bash
source setup_env.sh
```

To run the examples, ensure you have:
1. `TAPPAS_POST_PROC_DIR` environment variable set to the path of your TAPPAS installation (default: `/usr/lib/aarch64-linux-gnu/hailo/tappas/post-process`).
2. Hailo virtual environment activated.

### Install the Required Packages
Make sure you are in the virtual environment and run the following command:
```bash
pip install -r requirements.txt
```

### Download the Models (HEF files)
```bash
./download_resources.sh
```

## Running the Examples
After setting up the environment (source setup_env.sh), you can run the examples by running the following commands:
```bash
python hailo_rpi5_examples/detection.py --input resources/detection0.mp4
python hailo_rpi5_examples/pose_estimaton.py --input resources/detection0.mp4
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
python hailo_rpi5_examples/pose_estimaton.py --help
python hailo_rpi5_examples/instance_segmentation.py --help
```

## Adding Your Own Code
You can add your own code to the examples by editing the "app_callback" function in the examples. See the examples code for more details. In the examples, you'll also find an "app_callback_class" example to pass user data to the callback function. Each example has example code for parsing the metadata inferred by the network. Note that extracting the video frame and displaying it can slow down the application. The way it is used is not optimized and shown as a simple example.

## Contributing
We welcome contributions from the community.
For now, you can contribute by:
1. Opening a pull request.
2. Reporting issues and bugs.
3. Suggesting new features or improvements.
4. Join the discussion on the [Hailo Community Forum](https://community.hailo.ai/).

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
