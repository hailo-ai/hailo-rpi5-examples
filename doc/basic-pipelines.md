# Hailo RPi5 Basic Pipelines
This repository contains examples of basic pipelines for Hailo's RPi5 platform. The examples demonstrate object detection, human pose estimation, and instance segmentation.
It is built to allow you to use these applications as a basis for your own projects.

## Installation
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

### Resources Download
```bash
./download_resources.sh
```

## Application Structure

#### User defined data class (user_app_callback_class):
This is a user defined class to be used in the callback function. It inherits from ```hailo_rpi_common::app_callback_class``` and can be extended with user-defined variables and functions.
It is an example of how to extend the base callback class with additional variables and methods specific to the application.


#### Application Callback function (app_callback): 
**This is where you should add your code.** A user-defined callback function that processes each frame passing through the pipeline. Each example includes code for parsing the metadata inferred by the network.
This callback is called from the "identity_callback" element in the pipeline. It is placed after the network inference and the post process. So the buffer you get includes the network output, as Hailo Metadata, and the actual frame passed in the pipeline. You can use the user_app_callback_class to pass data between the main application and the callback. See for example how user frames are sent to display in the examples. For details about getting the frame buffer itself see [Using the frame buffer section](#using-the-frame-buffer).
For more information about Hailo Metadata objects see [Hailo Objects API](https://github.com/hailo-ai/tappas/blob/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/docs/write_your_own_application/hailo-objects-api.rst#L4) in the Tappas documentation.

#### Gstreamer Application Class (GStreamerApp):
**For using the basic pipelines you don't need to change this class.**
This is the class which set up the GStreamer pipeline and handles events and callbacks. It inherits from ```hailo_rpi_common::GStreamerApp```.
Each application can change the network parameters and the pipeline used. The pipeline is defined by overloading the ```get_pipeline_string``` function.
For more information about TAPPAS pipelines and elements see [TAPPAS Documentation](https://github.com/hailo-ai/tappas/blob/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/docs/TAPPAS_architecture.rst).

# Detection Example
![Banner](images/detection.gif)
This example demonstrates object detection. It uses YOLOv6n model.
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
The Callback function showcases how to get the instance segmentation metadata from the network output. Each instance is represented as a ```HAILO_DETECTION``` with a mask (```HAILO_CONF_CLASS_MASK``` object). If ```--use-frame``` flag is set the code will parse the masks, resize and reshape them according to the frame cooordinates. It will print their shape to the terminal. Drawing the mask on the user buffer is possible but not implemented in this example due to performance reasons.

## Additional features:
### Running with Different Input Sources
These examples run with a USB camera by default (/dev/video0). You can change the input source using the --input flag. To run with a Raspberry Pi camera, use `--input rpi`. Here are a few examples:
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
To print the frame rate add the `--print-fps` flag. This will print the frame rate to the terminal and to the video output window.

