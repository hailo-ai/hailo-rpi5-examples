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

### Quick Installation
Run the following script to automate the installation process:
```bash
./install.sh
```
### Manual Installation (Use Only if Quick Installation Was Not Performed)
Alternatively, you can manually perform the setup using the steps below.

1. ### Environment Configuration  (Required for Each New Terminal Session)
    Ensure your environment is set up correctly by sourcing the provided script. This script sets the required environment variables and activates the Hailo virtual environment. If the virtual environment does not exist, it will be created automatically.
    ```bash
    source setup_env.sh
    ```

2. ### Requirements Installation
    Within the activated virtual environment, install the necessary Python packages:
    ```bash
    pip install -r requirements.txt
    ```

    **Note:** The `rapidjson-dev` package is typically installed by default on Raspberry Pi OS. If it's missing, install it using:
    ```bash
    sudo apt install -y rapidjson-dev
    ```

3. ### Resources Download
    Download the required resources by running:
    ```bash
    ./download_resources.sh
    ```
    To download all models , You should use the `--all` with the ./download_resources.sh

4. ### Post Process Compilation
    This will compile post process files required for the demos. You can review the code in the `cpp` directory and tweak it as needed.
    ```bash
    ./compile_postprocess.sh
    ```

# Detection Example
![Banner](images/detection.gif)

This example demonstrates object detection using the YOLOv8s model for Hailo-8L (13 TOPS) and the YOLOv8m model for Hailo-8 (26 TOPS) by default. It also supports all models compiled with HailoRT NMS post process. Hailo's Non-Maximum Suppression (NMS) layer is integrated into the HEF file, allowing any detection network compiled with NMS to function with the same codebase.

### To Run the Example:
When opening a new terminal session, ensure you have sourced the environment setup script:
```bash
source setup_env.sh
```
Run the detection example:
```bash
python basic_pipelines/detection.py
```
- To close the application, press `Ctrl+C`.
#### Example For Using USB camera input (webcam):
   Detect the available camera using this script:
  ```bash
  get-usb-camera
  ```
  Run example using USB camera - Use the device found by the previous script:

  ```bash
  python basic_pipelines/detection.py --input /dev/video<X>
  ```

#### Example For Using Raspberry Pi Camera input:
  ```bash
  python basic_pipelines/detection.py --input rpi
  ```

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

The `download_resources.sh` script downloads the network trained in the [Retraining Example](retraining-example.md#using-yolov8-retraining-docker), which can be used as a reference.

To download all models , You should use the `--all` with the ./download_resources.sh

**Example:**
```bash
python basic_pipelines/detection.py --labels-json resources/barcode-labels.json --hef resources/yolov8s-hailo8l-barcode.hef --input resources/barcode.mp4
```

**Example Output:**
![Barcode Detection Example](images/barcode-example.png)

# Pose Estimation Example
![Banner](images/pose_estimation.gif)

This example demonstrates human pose estimation using the `yolov8s_pose` model for Hailo-8 Lite (H8l) and the `yolov8m_pose` model for Hailo-8 (H8)

### To Run the Example:
When opening a new terminal session, ensure you have sourced the environment setup script:
```bash
source setup_env.sh
```
Run the example:
```bash
python basic_pipelines/pose_estimation.py
```
Run example using Pi camera:
```bash
python basic_pipelines/pose_estimation.py --input rpi
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

This example demonstrates instance segmentation using the `yolov5n_seg` model for Hailo-8 Lite (H8l) and the `yolov5m_seg` model for Hailo-8 (H8).

### To Run the Example:
When opening a new terminal session, ensure you have sourced the environment setup script:
```bash
source setup_env.sh
```
Run the example:
```bash
python basic_pipelines/instance_segmentation.py
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
[Hailo Raspberry Pi Common Utilities](https://github.com/hailo-ai/hailo-apps-infra/blob/master/doc/development_guide.md)