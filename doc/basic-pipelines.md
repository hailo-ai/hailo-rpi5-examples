# Hailo RPi5 Basic Pipelines
This repository contains examples of basic pipelines for Hailo's RPi5 platform. The examples demonstrate object detection, human pose estimation, and instance segmentation.
It is built to allow you to use these applications as a basis for your own projects.

## Installation
### Clone the Repository
```bash
git clone https://github.com/hailo-ai/hailo-rpi5-examples.git
```
Enter the repository directory:
```bash
cd hailo-rpi5-examples
```

### Environment Configuration
To run the examples, you should ensure your environment is set up correctly. We use the hailo-tappas-core pkgconfig file to get Hailo dependencies.

You can set it all up by sourcing the following script. This script will set the required environment variables and activate Hailo virtual environment (if it doesn't exist, it will create it).
```bash
source setup_env.sh
```

### Requirements Installation
Make sure you are in the virtual environment and run the following command:
```bash
pip install -r requirements.txt
```

The rapidjson-dev package should be installed as default in Pi OS.
If for some reasone you don't have it you can install it using:
```bash
sudo apt install -y rapidjson-dev
```

### Resources Download
```bash
./download_resources.sh
```
### Post Process Compilation
The post process required is already merged to TAPPAS core from version 3.29.0. It will be removed from this repository in the future.
If you are using an older version you can compile the post process using the following script:
```bash
./compile_postprocess.sh
```
Note: If you are an using older version the app might still work but the labels will be wrong. In that case you should compile the post process.

## Application Structure

#### User-defined Data Class (user_app_callback_class)
This user-defined class is passed as an input to the callback function, which runs on the pipeline output. It is used for communication between the main application and the callback function. It extends `hailo_rpi_common::app_callback_class` and can be customized with additional variables and methods specific to the application.

#### Application Callback Function (app_callback)
**This is where you should add your code.** A user-defined function that processes each frame in the pipeline. It is called from the "identity_callback" element in the pipeline, placed after the network inference and post-processing. The GStreamer buffer passed as an input to this function includes the network output as Hailo Metadata and the frame itself. Each example demonstrates how to parse the specific metadata for its task. For more information on Hailo Metadata objects, refer to the [Hailo Objects API](https://github.com/hailo-ai/tappas/blob/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/docs/write_your_own_application/hailo-objects-api.rst#L4) in the TAPPAS documentation.

#### GStreamer Application Class (GStreamerApp)
**No changes needed for using the basic pipelines.** This class sets up the GStreamer pipeline and handles events and callbacks, extending `hailo_rpi_common::GStreamerApp`. Applications can modify network parameters and the pipeline by overloading the `get_pipeline_string` function. For more details on TAPPAS pipelines and elements, see the [TAPPAS Documentation](https://github.com/hailo-ai/tappas/blob/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/docs/TAPPAS_architecture.rst).



# Detection Example
![Banner](images/detection.gif)

This example demonstrates object detection. It uses YOLOv6n model as default. It supports also yolov8s and yolox_s_leaky models.
It uses Hailo's NMS (Non-Maximum Suppression) layer as part of the HEF file, so all detection networks which are compiled with NMS can be used with the same code.

#### To run the example use:
```bash
python basic_pipelines/detection.py --input resources/detection0.mp4
```
##### To close the application press 'Ctrl+C'.

For additional options run:
```bash
python basic_pipelines/detection.py --help
```
See also [Running with Different Input Sources](#running-with-different-input-sources).

## What is in this example:
#### Custom Callback Class:
This is an example of a custom callback class. It can be used to send user-defined data to the callback function. It inherits from the app_callback_class and can be extended with user-defined variables and functions. In this example we added a variable and a function to the class. These are used in the callback function when under the ```--use-frame``` flag. These values are then displayed on the user frame.

#### Application Callback function:
In this function we see example how to parse ```HAILO_DETECTION``` metadata. Each Gstreamer buffer include ```HAILO_ROI``` object. This object is the root of all Hailo metadata objects attached to this buffer. All detections are read an their label, bounding box and confidence are extracted. For this example we assume you have a "person" nearby. All detections are parsed and the number of persons detected is counted. The information for each person detected is printed to terminal.
If the ```--use-frame``` flag is used, the frame is extracted from the buffer and displayed. The number of persons detected is displayed on the frame. In addition, the user-defined data is displayed on the frame.

#### Additional features:
In this example we show and example how to add more options to the command line. The options are parsed using the argparse library. The added flag in this example is used to change the model used.

#### Using Retrained Models:

This application includes support for using retrained detection models. The model should be compiled with HailoRT NMS Post Process (HailortPP). To use a custom model, you can load its HEF using the `--hef-path` flag. The default labels used by our models are COCO labels ([80 classes](https://github.com/hailo-ai/tappas/blob/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/core/hailo/libs/postprocesses/common/labels/coco_eighty.hpp)). If you are using a custom model with different labels, you can use the `--labels-path` flag to load your labels file. For an example config file, see `hailo-rpi5-examples/resources/barcode-labels.json`.
The network we trained while writing the [Retraining Example](retraining-example.md#using-yolov8-retraining-docker) is downloaded by the `download_resources.sh` script. So you can use it as an example.

For example (using the RPi camera input):

```bash
python basic_pipelines/detection.py --labels-json resources/barcode-labels.json --hef resources/yolov8s-hailo8l-barcode.hef -i rpi
```
Example output:

![Barcode Detection Example](images/barcode-example.png)

# Pose Estimation Example
![Banner](images/pose_estimation.gif)

This example demonstrates human pose estimation. It uses yolov8s_pose model.

#### To run the example use:
```bash
python basic_pipelines/pose_estimation.py --input resources/detection0.mp4
```
##### To close the application press 'Ctrl+C'.
For additional options run:
```bash
python basic_pipelines/pose_estimation.py --help
```
See also [Running with Different Input Sources](#running-with-different-input-sources).
## What is in this example:
#### Pose Estimation Callback Class:
The Callback function showcases how to get the pose estimation metadata from the network output. Each pesron is represented as a ```HAILO_DETECTION``` with 17 keypoints (```HAILO_LANDMARKS``` objects). The code parses the landmarks and extracts the left and right eye coordinates and prints them to the terminal. If ```--use-frame``` flag is set the eyes will be drawn on the user frame.
The keypoints dictionary can be obtained from the ```get_keypoints``` function.

# Instance Segmentation Example
![Banner](images/instance_segmentation.gif)

This example demonstrates instance segmentation. It uses yolov5n_seg model.
#### To run the example use:
```bash
python basic_pipelines/instance_segmentation.py --input resources/detection0.mp4
```
##### To close the application press 'Ctrl+C'.
For additional options run:
```bash
python basic_pipelines/instance_segmentation.py --help
```
See also [Running with Different Input Sources](#running-with-different-input-sources).

## What is in this example:
#### Instance Segmentation Callback Class:
The Callback function showcases how to get the instance segmentation metadata from the network output. Each instance is represented as a ```HAILO_DETECTION``` with a mask (```HAILO_CONF_CLASS_MASK``` object). If ```--use-frame``` flag is set the code will parse the masks, resize and reshape them according to the frame coordinates. It will print their shape to the terminal. Drawing the mask on the user buffer is possible but not implemented in this example due to performance reasons.

## Additional features:
Run any example with the `--help` flag to see all available options.
For example:
```bash
python basic_pipelines/pose_estimation.py --help
# Example output:
usage: pose_estimation.py [-h] [--input INPUT] [--use-frame] [--show-fps] [--disable-sync] [--dump-dot]

Hailo App Help

options:
  -h, --help            show this help message and exit
  --input INPUT, -i INPUT
                        Input source. Can be a file, USB or RPi camera (CSI camera module). For RPi camera use '-i rpi' (Still in Beta). Defaults to
                        /dev/video0
  --use-frame, -u       Use frame from the callback function
  --show-fps, -f        Print FPS on sink
  --disable-sync        Disables display sink sync, will run as fast possible. Relevant when using file source.
  --dump-dot            Dump the pipeline graph to a dot file pipeline.dot
```
See more information on how to use these options below.

### Running with Different Input Sources
These examples run with a USB camera by default (/dev/video0). You can change the input source using the --input flag.
To run with a Raspberry Pi camera, use `--input rpi`. (Still in Beta)
Here are a few examples:
```bash
python basic_pipelines/detection.py --input /dev/video2
python basic_pipelines/detection.py --input rpi
python basic_pipelines/detection.py --input resources/detection0.mp4
```

Note: The USB camera is not guaranteed to be /dev/video0. You can check which video devices are available by running:
```bash
ls /dev/video*
```
You can test whether the camera is working by running:
```bash
ffplay -f v4l2 /dev/video0
```
If you get an error try another device, e.g. /dev/video2. (It will probably be an even number.)

#### Using the frame buffer:
For an example of using the frame buffer add the `--use-frame` flag. Note that extracting the video frame and displaying it can slow down the application. The way it is implemented is not optimized and is shown as a simple example. There is a possibility to write on the buffer and replace the old buffer in the pipeline however this is not efficient.

#### Printing the frame rate:
To print the frame rate add the `--show-fps` flag. This will print the frame rate to the terminal and to the video output window.

#### Dumping the pipeline graph:
This is useful for debugging and understanding the pipeline.
To dump the pipeline graph to a dot file add the `--dump-dot` flag. This will create a file called pipeline.dot in the basic_pipelines directory. You can then visualize the pipeline using a tool like [Graphviz](https://graphviz.org/).
To install it run:
```bash
sudo apt install graphviz
```
Here is a full example of running the detection example with the `--dump-dot` flag:
```bash
python basic_pipelines/detection.py --dump-dot
# To visulaize the pipeline run:
dot -Tx11 basic_pipelines/pipeline.dot &
# To save the pipeline as a png run:
dot -Tpng basic_pipelines/pipeline.dot -o pipeline.png
```
Here is an example output of the detection pipeline graph:
![detection_pipeline](images/detection_pipeline.png)
Tip: Right click on the image and select "Open image in new tab" to see the full image.

# Troubleshoting and Known Issues
If you encounter any issues, please open a ticket in the [Hailo Community Forum](https://community.hailo.ai/).
It is full with useful information and might already include the solution to your problem.

- RPi camera input is still in Beta. It might not be stable and can cause the application to crash.
- The frame buffer is not optimized and can slow down the application. It is shown as a simple example.
- **DEVICE_IN_USE() error.**
The `DEVICE_IN_USE()` error typically indicates that the Hailo device (usually `/dev/hailo0`) is currently being accessed or locked by another process. This can happen during concurrent access attempts or if a previous process did not terminate cleanly, leaving the device in a locked state. See community forum [topic](https://community.hailo.ai/t/resolving-device-in-use-error-for-hailo-devices/18?u=giladn) for more information.

  **Steps to Resolve:**

  1. **Identify the Device:**
  Typically, the Hailo device is located at `/dev/hailo0`. Ensure that this is the correct device file for your setup.

  2. **Find Processes Using the Device:**
  Run the following command to list any processes currently using the Hailo device:
  ```bash
  sudo lsof /dev/hailo0
  ```
  3. **Terminate Processes:**
  Use the PID (Process ID) from the output of the previous command to terminate the process. Replace `<PID>` with the actual PID.
  ```bash
  sudo kill -9 <PID>
  ```
