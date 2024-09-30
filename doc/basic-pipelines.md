# Hailo RPi5 Basic Pipelines
This repository contains examples of basic pipelines using Hailo's H8 and H8L accelerators. The examples demonstrate object detection, human pose estimation, and instance segmentation, providing a solid foundation for your own projects.

## Installation

### Clone the Repository
```bash
git clone https://github.com/hailo-ai/hailo-rpi5-examples.git
```
Navigate to the repository directory:
```bash
cd hailo-rpi5-examples
```

### Environment Configuration
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

### Post Process Compilation
The post-process functionality is integrated into the TAPPAS core starting from version 3.29.0 and will be deprecated in this repository in the future. If you are using an older version of TAPPAS, compile the post-process using:
```bash
./compile_postprocess.sh
```
**Note:** Using an older version without compiling the post-process may result in incorrect labels.

# Detection Example
![Banner](images/detection.gif)

This example showcases object detection using the YOLOv6n model by default. It also supports `yolov8s` and `yolox_s_leaky` models. Hailo's Non-Maximum Suppression (NMS) layer is integrated into the HEF file, allowing any detection network compiled with NMS to function with the same codebase.

### To Run the Example:
```bash
python basic_pipelines/detection.py --input resources/detection0.mp4
```
##### To close the application, press `Ctrl+C`.

For additional options, execute:
```bash
python basic_pipelines/detection.py --help
```
Refer to [Running with Different Input Sources](#running-with-different-input-sources) for more details.

## What’s in This Example:

### Custom Callback Class
An example of a custom callback class that sends user-defined data to the callback function. Inherits from `app_callback_class` and can be extended with custom variables and functions. This example adds a variable and a function used when the `--use-frame` flag is active, displaying these values on the user frame.

### Application Callback Function
Demonstrates parsing `HAILO_DETECTION` metadata. Each GStreamer buffer contains a `HAILO_ROI` object, serving as the root for all Hailo metadata attached to the buffer. The function extracts the label, bounding box, and confidence for each detection, assuming the presence of a "person". It counts and prints the number of persons detected. With the `--use-frame` flag, it also displays the frame with the number of detected persons and user-defined data.

### Additional Features
Shows how to add more command-line options using the `argparse` library. For instance, the added flag in this example allows changing the model used.

### Using Retrained Models
Supports using retrained detection models compiled with HailoRT NMS Post Process (`HailortPP`). Load a custom model’s HEF using the `--hef-path` flag. Default labels are COCO labels ([80 classes](https://github.com/hailo-ai/tappas/blob/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/core/hailo/libs/postprocesses/common/labels/coco_eighty.hpp)). For custom models with different labels, use the `--labels-path` flag to load your labels file (e.g., `resources/barcode-labels.json`).

The `download_resources.sh` script downloads the network trained in the [Retraining Example](doc/retraining-example.md#using-yolov8-retraining-docker), which can be used as a reference.

**Example (using the RPi camera input):**
```bash
python basic_pipelines/detection.py --labels-json resources/barcode-labels.json --hef resources/yolov8s-hailo8l-barcode.hef -i rpi
```
**Example Output:**
![Barcode Detection Example](images/barcode-example.png)

# Pose Estimation Example
![Banner](images/pose_estimation.gif)

This example demonstrates human pose estimation using the `yolov8s_pose` model.

### To Run the Example:
```bash
python basic_pipelines/pose_estimation.py --input resources/detection0.mp4
```
##### To close the application, press `Ctrl+C`.

For additional options, execute:
```bash
python basic_pipelines/pose_estimation.py --help
```
Refer to [Running with Different Input Sources](#running-with-different-input-sources) for more details.

## What’s in This Example:

### Pose Estimation Callback Class
The callback function retrieves pose estimation metadata from the network output. Each person is represented as a `HAILO_DETECTION` with 17 keypoints (`HAILO_LANDMARKS` objects). The function parses the landmarks to extract the left and right eye coordinates, printing them to the terminal. If the `--use-frame` flag is set, the eyes are drawn on the user frame. Obtain the keypoints dictionary using the `get_keypoints` function.

# Instance Segmentation Example
![Banner](images/instance_segmentation.gif)

This example demonstrates instance segmentation using the `yolov5n_seg` model.

### To Run the Example:
```bash
python basic_pipelines/instance_segmentation.py --input resources/detection0.mp4
```
##### To close the application, press `Ctrl+C`.

For additional options, execute:
```bash
python basic_pipelines/instance_segmentation.py --help
```
Refer to [Running with Different Input Sources](#running-with-different-input-sources) for more details.

## What’s in This Example:

### Instance Segmentation Callback Class
The callback function processes instance segmentation metadata from the network output. Each instance is represented as a `HAILO_DETECTION` with a mask (`HAILO_CONF_CLASS_MASK` object). If the `--use-frame` flag is set, the function parses, resizes, and reshapes the masks according to the frame coordinates, printing their shape to the terminal. Drawing the mask on the user buffer is possible but not implemented in this example due to performance considerations.

# Development Guide
### Recommendations for Makers

- **Start Simple**: If you're new to the pipeline, begin with the basic scripts to familiarize yourself with the workflow.
- **Incremental Complexity**: Gradually move to more complex pipelines as you gain confidence and require more advanced features.
- **Leverage Documentation**: Refer to the [TAPPAS Documentation](https://github.com/hailo-ai/tappas/blob/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/docs/TAPPAS_architecture.rst) and [Hailo Objects API](https://github.com/hailo-ai/tappas/blob/4341aa360b7f8b9eac9b2d3b26f79fca562b34e4/docs/write_your_own_application/hailo-objects-api.rst#L4) for deeper insights and advanced customization options.

By following this guide, makers can efficiently utilize the `basic_pipelines` package to build and customize their computer vision applications without getting overwhelmed by complexity.

## Application Structure

The `basic_pipelines` package provides a range of scripts and modules designed to help you get started with various computer vision tasks. Whether you're a beginner or looking to implement more complex functionalities, the package accommodates different levels of complexity to suit your needs.

## Getting Started with Simple Examples

For those who prefer a straightforward approach, you can utilize the individual scripts such as `detection.py`, `pose_estimation.py`, and `instance_segmentation.py`. These scripts are designed to be easy to use:

- **Minimal Setup**: Simply run the script and focus on editing the callback function to customize how the output is processed.
- **Customize Callbacks**: Modify the `app_callback` function within each script to handle the pipeline output according to your specific requirements.

These scripts are importing the application code from the 'pipelines' scripts.

## Pipelines scripts for Enhanced Functionality

If you're looking to implement more sophisticated pipelines, scripts like `detection_pipeline.py`, `pose_estimation_pipeline.py`, and `instance_segmentation_pipeline.py` offer extended capabilities:

- **Comprehensive Implementation**: These scripts include additional code that manages the pipeline and application logic.
- **Leverage Common Utilities**: They utilize foundational functions and classes defined in `hailo_rpi_common.py`, enabling more complex operations and better modularity.
- **Customization Options**: You can override methods and adjust pipeline parameters to tailor the application to your specific needs.

### GStreamer Pipelines

GStreamer pipelines are constructed by chaining together individual elements. There are two primary methods to create a pipeline:

1. **Programmatic Approach**: Utilizing GStreamer's factory functions along with the `add` and `link` methods. Examples of this method can be found in the [GStreamer documentation](https://gstreamer.freedesktop.org/documentation/).

2. **String-Based Syntax**: Defining the pipeline using a string with the following syntax: `[element1]![element2]![element3]!..![elementN]`.

In our examples, we will use the second method. This approach allows you to describe the pipeline with a simple string, which can also be executed directly from the command line using the `gst-launch-1.0` command. This is the method used in the TAPPAS pipelines.

GStreamer is a powerful framework that enables the seamless flow of data between elements such as sources, filters, and sinks. For more detailed information on constructing pipelines, refer to the [GStreamer documentation](https://gstreamer.freedesktop.org/documentation/) and the [TAPPAS Architecture documentation](https://github.com/hailo-ai/tappas/blob/master/docs/TAPPAS_architecture.rst).

## Hailo Raspberry Pi Common Utilities
The `hailo_rpi_common.py` file contains shared classes and functions that support the various pipeline scripts:

- **GStreamerApp Class**: Manages the GStreamer pipeline, handling events and callbacks.
- **App Callback Class**: Facilitates communication between the main application and callback functions, allowing for easy customization and extension.
- **pipeline helper functions** These functions are designed to encapsulate GStreamer pipelines, enabling developers to build robust and efficient pipelines without delving into the complexities of GStreamer syntax.


## Pipeline Helper Functions
Instead of manually crafting GStreamer pipelines, it is highly recommended to utilize the **pipeline helper functions** provided in `basic_pipelines/hailo_rpi_common.py`. This approach not only streamlines the development process but also ensures that best practices are consistently applied across all pipeline scripts. Queues also enfoces

### `QUEUE`

**Description:**
Creates a GStreamer `queue` element with configurable parameters. Queues are essential for managing the flow of data between different pipeline elements, ensuring smooth and efficient processing.It is also used to enable multithreading. A queue will create a new thread on its output, allowing different parts of the pipeline to run in parallel. See [Gstreamer Multithreading documentation](https://gstreamer.freedesktop.org/documentation/tutorials/basic/handy-elements.html#multithreading) for more details.

**Usage:**
Use the `QUEUE` function to insert buffering points in your pipeline, controlling the number of buffers, bytes, and time the queue can handle, as well as its leak behavior.

**For more details, refer to the [`QUEUE` function in `hailo_rpi_common.py`](../basic_pipelines/hailo_rpi_common.py).**

### `SOURCE_PIPELINE`

**Description:**
Generates a GStreamer pipeline string tailored to the specified video source type (e.g., Raspberry Pi camera, USB camera, or file). It automatically configures essential properties such as format, width, and height based on the source.

**Usage:**
Utilize the `SOURCE_PIPELINE` function to create the source segment of your pipeline without manually specifying each element and property.

**For more details, refer to the [`SOURCE_PIPELINE` function in `hailo_rpi_common.py`](../basic_pipelines/hailo_rpi_common.py).**

---

### `INFERENCE_PIPELINE`

**Description:**
Constructs a GStreamer pipeline string for performing inference and post-processing using user-provided HEF files and shared object (`.so`) post processing files. Integrates Hailo's inference engine (`hailonet`) and post-processing (`hailofilter`) elements seamlessly.

**Usage:**
Use the `INFERENCE_PIPELINE` function to set up the inference stage of your pipeline, specifying parameters like batch size, configuration files, and additional processing options.

**For more details, refer to the [`INFERENCE_PIPELINE` function in `hailo_rpi_common.py`](../basic_pipelines/hailo_rpi_common.py).**

---

### `DETECTION_PIPELINE`

**Description:**
Builds a GStreamer pipeline string specifically for detection tasks using HailoRT post-processing. This pipeline is optimized for detection models compiled with HailoRT post-processing capabilities.

**Usage:**
Leverage the `DETECTION_PIPELINE` function to create a detection-focused pipeline segment, providing paths to HEF files and label configurations as needed.

**For more details, refer to the [`DETECTION_PIPELINE` function in `hailo_rpi_common.py`](../basic_pipelines/hailo_rpi_common.py).**

---

### `INFERENCE_PIPELINE_WRAPPER`

**Description:**
Wraps an existing inference pipeline with `hailocropper` and `hailoaggregator` elements. This wrapper maintains the original video resolution and color space, ensuring seamless integration with complex pipelines.

**Usage:**
Use the `INFERENCE_PIPELINE_WRAPPER` function to encapsulate your inference pipeline, facilitating advanced processing like cropping and aggregation without altering the original pipeline's properties.
**Note:** The post process will have to warp the network output to the 'original' resolution. This is not yet implemented in all post processes and metadata types.

**For more details, refer to the [`INFERENCE_PIPELINE_WRAPPER` function in `hailo_rpi_common.py`](../basic_pipelines/hailo_rpi_common.py).**

---

### `DISPLAY_PIPELINE`

**Description:**
Generates a GStreamer pipeline string for displaying video output. Incorporates the `hailooverlay` plugin to render bounding boxes and labels, enhancing the visual output of processed frames.

**Usage:**
Utilize the `DISPLAY_PIPELINE` function to add a display segment to your pipeline, with options to enable FPS overlay and configure the video sink.

**For more details, refer to the [`DISPLAY_PIPELINE` function in `hailo_rpi_common.py`](../basic_pipelines/hailo_rpi_common.py).**

---

### `USER_CALLBACK_PIPELINE`

**Description:**
Creates a GStreamer pipeline string for integrating a user-defined callback element. This allows developers to inject custom processing logic at specific points within the pipeline.

**Usage:**
Use the `USER_CALLBACK_PIPELINE` function to add a callback stage to your pipeline, enabling custom data handling and processing as needed.

**For more details, refer to the [`USER_CALLBACK_PIPELINE` function in `hailo_rpi_common.py`](../basic_pipelines/hailo_rpi_common.py).**


## Additional Features
Run any example with the `--help` flag to view all available options.

**Example:**
```bash
python basic_pipelines/pose_estimation.py --help
# Example output:
usage: pose_estimation.py [-h] [--input INPUT] [--use-frame] [--show-fps] [--disable-sync] [--dump-dot]

Hailo App Help

options:
  -h, --help            show this help message and exit
  --input INPUT, -i INPUT
                        Input source. Can be a file, USB or RPi camera (CSI camera module). For RPi camera use '-i rpi' (Still in Beta). Defaults to /dev/video0
  --use-frame, -u       Use frame from the callback function
  --show-fps, -f        Print FPS on sink
  --disable-sync        Disables display sink sync, will run as fast as possible. Relevant when using file source.
  --dump-dot            Dump the pipeline graph to a dot file pipeline.dot
```
Refer to the following sections for more information on using these options.

### Running with Different Input Sources
By default, these examples use a USB camera (`/dev/video0`). You can change the input source using the `--input` flag.

**To use a Raspberry Pi camera:**
```bash
python basic_pipelines/detection.py --input rpi
```
*(Still in Beta)*

**Other examples:**
```bash
python basic_pipelines/detection.py --input /dev/video2
python basic_pipelines/detection.py --input rpi
python basic_pipelines/detection.py --input resources/detection0.mp4
```

**Note:** The USB camera device might not always be `/dev/video0`. To check available video devices:
```bash
ls /dev/video*
```
**Test the camera functionality:**
```bash
ffplay -f v4l2 /dev/video0
```
If an error occurs, try a different device (e.g., `/dev/video2`), typically an even-numbered device.

#### Using the Frame Buffer
To utilize the frame buffer, add the `--use-frame` flag. Be aware that extracting and displaying video frames can slow down the application due to non-optimized implementation. Writing to the buffer and replacing the old buffer in the pipeline is possible but inefficient.

#### Printing the Frame Rate
To display the frame rate, add the `--show-fps` flag. This will print the FPS to both the terminal and the video output window.

#### Dumping the Pipeline Graph
Useful for debugging and understanding the pipeline structure. To dump the pipeline graph to a DOT file, add the `--dump-dot` flag:
```bash
python basic_pipelines/detection.py --dump-dot
```
This creates a file named `pipeline.dot` in the `basic_pipelines` directory.

**Visualize the pipeline using Graphviz:**
1. **Install Graphviz:**
    ```bash
    sudo apt install graphviz
    ```
2. **Visualize the pipeline:**
    ```bash
    dot -Tx11 basic_pipelines/pipeline.dot &
    ```
3. **Save the pipeline as a PNG:**
    ```bash
    dot -Tpng basic_pipelines/pipeline.dot -o pipeline.png
    ```
**Example Output:**
![detection_pipeline](images/detection_pipeline.png)
*Tip: Right-click the image and select "Open image in new tab" to view the full image.*

# Troubleshooting and Known Issues
If you encounter any issues, please open a ticket in the [Hailo Community Forum](https://community.hailo.ai/). The forum is a valuable resource filled with useful information and potential solutions.

**Known Issues:**
- **RPi Camera Input (Beta):** The Raspberry Pi camera input is currently in Beta. It may not be stable and could cause the application to crash.
- **Frame Buffer Performance:** The frame buffer extraction and display are not optimized, potentially slowing down the application. It is provided as a simple example.
- **DEVICE_IN_USE() Error:**
  The `DEVICE_IN_USE()` error indicates that the Hailo device (usually `/dev/hailo0`) is being accessed or locked by another process. This can occur during concurrent access attempts or if a previous process did not terminate cleanly.

  **Steps to Resolve:**

  1. **Identify the Device:**
     Ensure that `/dev/hailo0` is the correct device file for your setup.

  2. **Find Processes Using the Device:**
     List any processes currently using the Hailo device:
     ```bash
     sudo lsof /dev/hailo0
     ```

  3. **Terminate Processes:**
     Use the PID (Process ID) from the previous command's output to terminate the process. Replace `<PID>` with the actual PID:
     ```bash
     sudo kill -9 <PID>
     ```
