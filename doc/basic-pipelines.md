# Hailo RPi5 Basic Pipelines
This repository contains examples of basic pipelines using Hailo's H8 and H8L accelerators. The examples demonstrate object detection, human pose estimation, and instance segmentation, providing a solid foundation for your own projects.
This repo is using our [Hailo Apps Infra](https://github.com/hailo-ai/hailo-apps-infra) repo as a dependency.
See our Development Guide for more information on how to use the pipelines to create your own custom pipelines.

## Installation
See the [Installation Guide](../README.md#installation) in the main README for detailed instructions on setting up your environment.

# Overview

This guide provides an overview of how to develop custom applications using the basic pipelines provided in this repository. The examples demonstrate object detection, human pose estimation, and instance segmentation using Hailo's H8 and H8L accelerators.

## Understanding the Callback Method

Each example in this repository uses a callback method to process the data from the GStreamer pipeline. The callback method is defined as a function that is called whenever data is available from the pipeline. This function processes the data, extracts relevant information, and performs any necessary actions, such as drawing on a frame or printing information to the terminal.

### User App Callback Class

The `user_app_callback_class` is a custom class that inherits from the `app_callback_class` provided by the `hailo_apps_infra` package. This class is used to manage user-specific data and state across multiple frames. It typically includes methods to increment frame counts, manage frame data, and handle any additional user-specific logic.

### Note on Callback Function

The callback function is blocking and cannot take too long to execute; otherwise, the pipeline will get stuck. If you need a long processing time per frame, send the data to another process. For example, see the `WLEDDisplay` class in the `community_projects/wled_display/wled_display.py` file and the callbacks using it, such as in `community_projects/wled_display/wled_pose_estimation.py`. The `WLEDDisplay` class runs its own process, which gets data from the application callback and processes it in the background, allowing the pipeline to continue.

## Available Pipelines

The basic pipelines examples use the `hailo-apps-infra` package, which provides common utilities and the actual pipelines. You can import and use these pipelines in your applications. Below are some of the available pipelines:


# Detection Example
![Banner](images/detection.gif)

This example demonstrates object detection using the YOLOv8s model for Hailo-8L (13 TOPS) and the YOLOv8m model for Hailo-8 (26 TOPS) by default. It also supports all models compiled with HailoRT NMS post process. Hailo's Non-Maximum Suppression (NMS) layer is integrated into the HEF file, allowing any detection network compiled with NMS to function with the same post process.
All "persons" are tracked.

## What’s in This Example:

### Custom Callback Class
An example of a custom callback class that sends user-defined data to the callback function. Inherits from `app_callback_class` and can be extended with custom variables and functions. This example adds a variable and a function used when the `--use-frame` flag is active, displaying these values on the user frame.

### Application Callback Function
Demonstrates parsing `HAILO_DETECTION` metadata. Each GStreamer buffer contains a `HAILO_ROI` object, serving as the root for all Hailo metadata attached to the buffer. The function extracts the label, bounding box, confidence and tracking ID for each 'Person' detection. It counts and prints the number of persons detected. With the `--use-frame` flag, it also displays the frame with the number of detected persons and user-defined data. Most detection networks

### Additional Features
Shows how to add more command-line options using the `argparse` library. For instance, the added flag in this example allows changing the model used.

### Additional Supported Models
By default, the package contains a single model depending on the device architecture.
You can download additional models by running `hailo-download-resources --all`.
The models are downloaded to the `resources/models/` directory.
This application supports all models that are compiled with HailoRT NMS post process.

### Using Retrained Models
The retrain guide is available in the [Hailo Apps Infra repo: Retraining Example](https://github.com/hailo-ai/hailo-apps-infra/blob/main/doc/developer_guide/retraining_example.md).


# Pose Estimation Example
![Banner](images/pose_estimation.gif)

This example demonstrates human pose estimation using the `yolov8s_pose` model for Hailo-8l (13 TOPS) and the `yolov8m_pose` model for Hailo-8 (26 TOPS).

## What’s in This Example:

### Pose Estimation Callback Class
The callback function retrieves pose estimation metadata from the network output. Each person is represented as a `HAILO_DETECTION` with 17 keypoints (`HAILO_LANDMARKS` objects). The function parses the landmarks to extract the left and right eye coordinates, printing them to the terminal. If the `--use-frame` flag is set, the eyes are drawn on the user frame. Obtain the keypoints dictionary using the `get_keypoints` function.

### Keypoints Dictionary
The `get_keypoints` function provides a dictionary mapping keypoint names to their corresponding indices. This dictionary includes keypoints for the nose, eyes, ears, shoulders, elbows, wrists, hips, knees, and ankles.

### Frame Processing
If the `--use-frame` flag is set, the callback function retrieves the video frame from the buffer and processes it to draw the detected keypoints (left and right eyes) on the frame. The processed frame is then displayed.

# Instance Segmentation Example
![Banner](images/instance_segmentation.gif)

## What’s in This Example:

### Instance Segmentation Callback Class
The callback function processes instance segmentation metadata from the network output. Each instance is represented as a `HAILO_DETECTION` with a mask (`HAILO_CONF_CLASS_MASK` object). The function parses, resizes, and reshapes the masks according to the frame coordinates, and overlays the masks on the frame if the `--use-frame` flag is set. The function also prints the detection details, including the track ID, label, and confidence, to the terminal.

### Key Features
- **Frame Skipping**: Processes every 2nd frame to reduce computational load.
- **Color Coding**: Uses predefined colors to differentiate between tracked instances.
- **Mask Overlay**: Resizes and overlays the segmentation masks on the frame.
- **Boundary Handling**: Ensures the ROI dimensions are within the frame boundaries and handles negative values.

# Depth Estimation Example
![Banner](images/depth.gif)

This example demonstrates depth estimation using the `scdepthv3` model.

The result of depth estimation is essentially assigning each pixel in the image frame with an additional property - the distance from the camera.

For example:

Each pixel is represented by its position in the frame (x, y).

The value of the pixel might be represented by a trio of (Red, Green, Blue) values.

Depth estimation adds a fourth dimension to the pixel - the distance from the camera: (Red, Green, Blue, Distance).

However, it's important to familiarize yourself with the meaning of depth values, such as the fact that the distances might be relative, normalized, and unitless.
<u>Specifically, the results might not represent real-world distances from the camera to objects in the image.</u>
Please refer to the original [scdepthv3](https://arxiv.org/abs/2211.03660) paper for more details and the [hailo-apps-infra C++ post-processing](https://github.com/hailo-ai/hailo-apps-infra/tree/main/cpp).

## What’s in This Example:

### Application Callback Function
This function demonstrates parsing the `HAILO_DEPTH_MASK` depth matrix. Each GStreamer buffer contains a `HAILO_ROI` object, serving as the root for all Hailo metadata attached to the buffer. The function extracts the depth matrix for each frame buffer. The depth values are part of a separate matrix representing the frame with only depth values for each pixel (without the RGB values). For each depth matrix, using the User Application Callback Class, a logical calculation is performed and the result is printed to the terminal (CLI).

Note about frame sizing and rescaling: the scdepthv3 output frame size (depth matrix) is 320x256 pixels, which is typically smaller than the camera's frame size (resolution). The Hailo `INFERENCE_PIPELINE_WRAPPER` GStreamer pipeline element, which is part of the [depth GStreamer pipeline](https://github.com/hailo-ai/hailo-apps-infra/tree/main/hailo_apps_infra), rescales the depth matrix to the original frame size.

### User Application Callback Class
This class includes various methods for manipulating the depth results. In this example, we filter out the highest 5% of the values (treating them as outliers) and then calculate the average depth value across the frame.

# Development Recommendations

- **Start Simple**: If you're new to the pipeline, begin with the basic scripts to familiarize yourself with the workflow.
- **Minimal Setup**: Simply run the script and focus on editing the callback function to customize how the output is processed.
- **Customize Callbacks**: Modify the `app_callback` function within each script to handle the pipeline output according to your specific requirements.
- **Incremental Complexity**: Gradually move to more complex pipelines as you gain confidence and require more advanced features.
- **Leverage Documentation**: Refer to the [TAPPAS Documentation](https://github.com/hailo-ai/tappas/blob/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/docs/TAPPAS_architecture.rst) and [Hailo Objects API](https://github.com/hailo-ai/tappas/blob/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/docs/write_your_own_application/hailo-objects-api.rst#L4) for deeper insights and advanced customization options.
- **hailo-apps-infra package** - The pipelines used in the basic pipelines examples are using the hailo-app-infra package. This package provides common utilities and the actual pipelines. For more information see [Hailo apps infra Repo](https://github.com/hailo-ai/hailo-apps-infra/blob/master/doc/development_guide.md).

By following this guide, makers can efficiently utilize the `basic_pipelines` package to build and customize their computer vision applications without getting overwhelmed by complexity.

### Debugging Tips
#### Print Statements
The simplest tool for debugging is to use the `print` function. You can print the data you are interested in, such as the frame number, the number of detected objects, or the detected objects' coordinates. This can help you understand the data flow and identify any issues.
#### ipdb Debugger
The `ipdb` debugger is a powerful tool for debugging Python code. You can insert breakpoints in your code and inspect variables, step through the code, and evaluate expressions. To use `ipdb`, add the following line to your code where you want to set a breakpoint:
    ```python
    import ipdb; ipdb.set_trace()
    ```
```python
import ipdb; ipdb.set_trace()
```
When the code reaches this line, it will pause execution, and you can interact with the debugger. You can then step through the code, inspect variables, and evaluate expressions to identify issues. This tool is useful for discovering available options and methods for a given object or variable. Due to `ipdb` auto-complete feature, you can type the object name and press `Tab` to see the available options and methods.

Note that you need to install the `ipdb` package to use this debugger. You can install it using the following command:
```bash
pip install ipdb
```
#### Debugpy in VS Code
There is another option for IDE native debugging when working with VS Code. Please refer to the [following guide in Hailo community forum](https://community.hailo.ai/t/debugging-raspberry-pi-python-code-using-vs-code/12595)

#### Choppy Video Playback

If you experience choppy video playback, it might be caused due to too long processing time in the pipeline. This will casue frames to be dropped.
This can be cause by heavy compute in the callback function or in another place in the pipeline.
In the callback function, ensure that the processing time is minimal to avoid blocking the pipeline. If you need to perform heavy processing, consider sending the data to another process for processing in the background.
You can disable the callback function using the `--disable-callback` flag.
Another CPU intense consumer is video operations which are not accelerated on the RPi5. Consider using lower resolution or lower frame rate videos.
Run the `htop` command in a terminal to monitor the CPU and memory usage.
If the CPU usage is close to 100%, it might be the colprit.
If the CPU usage is low, the bottleneck could be the Hailo model.
In this case, consider using a smaller model or using larger batch size.
See the [Hailo Monitor](#hailo-monitor) section for more information on how to monitor the Hailo model.

#### Hailo monitor
To run the Hailo monitor, run the following command in a different terminal:
```bash
hailortcli monitor
```
In the terminal you run your code set the `HAILO_MONITOR` environment variable to `1` to enable the monitor.
```bash
export HAILO_MONITOR=1
```
#### Pipeline debugging
See [Hailo Apps Infra Developer Guide](https://github.com/hailo-ai/hailo-apps-infra/blob/main/doc/development_guide.md) for more information on how to debug the pipeline.


# Scripts Overview

### Environment Configuration  (Required for Each New Terminal Session)
Ensure your environment is set up correctly by sourcing the provided script. This script sets the required environment variables and activates the Hailo virtual environment. If the virtual environment does not exist, it will be created automatically.
```bash
source setup_env.sh
```

### Requirements Installation
Within the activated virtual environment, install the necessary Python packages:
```bash
pip install -r requirements.txt
```

**Note:** The `rapidjson-dev` package is typically installed by default on Raspberry Pi OS. If it's missing, install it using:
```bash
sudo apt install -y rapidjson-dev
```

### Resources Download
Download the required resources by running:
```bash
./download_resources.sh
```
To download all models, you should use the `--all` option with the `./download_resources.sh` script.
