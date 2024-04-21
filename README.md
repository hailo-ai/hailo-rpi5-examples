# hailo_rpi5_examples
This repository contains examples for running Hailo's AI processor on Raspberry Pi 5

## Pre-requisites:
You should have Hailo's Driver and software installed on your Raspberry Pi 5.
Hailo TAPPAS installation is required for running the examples.
### For installation instructions see [install-raspberry-pi5.md](doc/install-raspberry-pi5.md)

#### To run the examples, you should make sure your envirenmet is set up correctly.
We require hailo pkgconfig file to be in the `PKG_CONFIG_PATH`.
To run the examples, you should have:
1. `TAPPAS_LIBDIR` environment variable set to the path of your TAPPAS installation. (/opt/hailo/tappas/lib/aarch64-linux-gnu)
2. Hailo virtual environment activated.

You can set it all up by sourcing the following script:
```bash
source setup_env.sh
```

#### Install the required packages:
```bash
pip install -r requirements.txt
```

#### Download the models HEF files:
```bash
./download_resources.sh
```

## Runnign the examples:
After setting up the environment (source setup_env.sh), you can run the examples by running the following commands:
```bash
python hailo_rpi5_examples/detection.py
python hailo_rpi5_examples/pose_estimaton.py
python hailo_rpi5_examples/instance_segmentation.py
```

This examples are running with a USB camera as default. (/dev/video0)
You can change the input source by using the --input flag.
To run with a Raspberry Pi camera, you can use --input rpi
Here are a few examples:
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

## Adding your own code:
You can add your own code to the examples by editing the "app_callback" function in the examples.
See the examples code for more details.
In the examples you'll also find an "app_callback_class" example to pass user data to the callback function.
Each example has example code for parsing the metadata inferred by the network.
The applications has also a flag to enable using the video frame.
Note that extracting the video frame and displaying it can slow down the application.
The way it is used is not optimized and shown as a simple example.
