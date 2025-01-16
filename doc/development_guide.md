
# Development Guide
The `gstreamer_app.py` file contains shared classes that support the various pipeline scripts:

## GStreamerApp Class

The `GStreamerApp` class is a central component for managing GStreamer pipelines in your applications. It handles the creation, configuration, and execution of GStreamer pipelines, as well as managing events and callbacks. This class simplifies the process of integrating GStreamer with your application, allowing you to focus on your specific application1 logic.

- **GStreamerApp Class**: Manages the GStreamer pipeline, handling events and callbacks.
- **App Callback Class**: Facilitates communication between the main application and callback functions, allowing for easy customization and extension.
- **pipeline helper functions** These functions are designed to encapsulate GStreamer pipelines, enabling developers to build robust and efficient pipelines without delving into the complexities of GStreamer syntax.

### Key Features

- **Pipeline Management**: Creates and manages the GStreamer pipeline, including setting up the pipeline string and handling state transitions.
- **Event Handling**: Manages GStreamer events such as End-of-Stream (EOS), errors, and Quality of Service (QoS) messages.
- **Callback Integration**: Integrates user-defined callback functions to process data from the pipeline.
- **Signal Handling**: Sets up signal handlers for graceful shutdown on receiving SIGINT (Ctrl-C).
- **Frame Processing**: Supports frame extraction and processing using a multiprocessing queue.

### Initialization

The `GStreamerApp` class is initialized with command-line arguments and a user-defined callback class. The callback class should inherit from `app_callback_class` and manage user-specific data and state.

### Creating the Pipeline

The `create_pipeline` method initializes GStreamer, constructs the pipeline string, and sets up the pipeline. This method uses the `get_pipeline_string` method to generate the pipeline string. This method should be overridden in your pipeline to customize the pipeline construction.
GStreamer pipelines are constructed by chaining together individual elements. There are two primary methods to create a pipeline:

1. **Programmatic Approach**: Utilizing GStreamer's factory functions along with the `add` and `link` methods. Examples of this method can be found in the [GStreamer documentation](https://gstreamer.freedesktop.org/documentation/).

2. **String-Based Syntax**: Defining the pipeline using a string with the following syntax: `[element1]![element2]![element3]!..![elementN]`.

In our examples, we will use the second method. This approach allows you to describe the pipeline with a simple string, which can also be executed directly from the command line using the `gst-launch-1.0` command. This is the method used in the TAPPAS pipelines.

GStreamer is a powerful framework that enables the seamless flow of data between elements such as sources, filters, and sinks. For more detailed information on constructing pipelines, refer to the [GStreamer documentation](https://gstreamer.freedesktop.org/documentation/) and the [TAPPAS Architecture documentation](https://github.com/hailo-ai/tappas/blob/master/docs/TAPPAS_architecture.rst).

You can write your own pipeline string or use the [Pipeline helper functions](#pipeline-helper-functions) provided in this repo to simplify the process.

### Running the Pipeline

The `run` method sets up the pipeline bus, connects the callback function, and starts the GLib event loop.

### Handling Events

The `bus_call` method handles GStreamer events such as End-of-Stream (EOS), errors, and Quality of Service (QoS) messages.
The `shutdown` method handles graceful shutdown of the pipeline and the GLib event loop.
The EOS event can be used to rewind the video source for continuous playback.

### Additional Features
We supply additional features to help you build your own pipelines and applications. Which is integrated with the GstreamerApp class. These features include:
- Argument parsing and help menu.
- Hailo architecture detection.
- USB camera detection.
See [haio_rpi_common.py](../hailo_apps_infra/hailo_rpi_common.py) for more information.
Run any example with the `--help` flag to view all available options.

### Example Usage
For examples how to inherit from and use the `GStreamerApp` class, refer to the pipeline scripts in this repository.
[pose_estimation_pipeline.py](../hailo_apps_infra/pose_estimation_pipeline.py) is a good starting point.

## Pipeline Helper Functions
Instead of manually crafting GStreamer pipelines, it is highly recommended to utilize the **pipeline helper functions** provided in `hailo_apps_infra/gstreamer_helper_pipelines.py`. This approach not only streamlines the development process but also ensures that best practices are consistently applied across all pipeline scripts.

### `SOURCE_PIPELINE`

**Description:**
Generates a GStreamer pipeline string tailored to the specified video source type (e.g., Raspberry Pi camera, USB camera, or file). It automatically configures essential properties such as format, width, and height based on the source.

**Usage:**
Utilize the `SOURCE_PIPELINE` function to create the source segment of your pipeline without manually specifying each element and property.

**For more details, refer to the [`SOURCE_PIPELINE` function in `gstreamer_helper_pipelines.py`](hailo_apps_infra/gstreamer_helper_pipelines.py).**

---

### `INFERENCE_PIPELINE`

**Description:**
Constructs a GStreamer pipeline string for performing inference and post-processing using user-provided HEF files and shared object (`.so`) post processing files. Integrates Hailo's inference engine (`hailonet`) and post-processing (`hailofilter`) elements seamlessly.

**Usage:**
Use the `INFERENCE_PIPELINE` function to set up the inference stage of your pipeline, specifying parameters like batch size, configuration files, and additional processing options.

**For more details, refer to the [`INFERENCE_PIPELINE` function in `gstreamer_helper_pipelines.py`](hailo_apps_infra/gstreamer_helper_pipelines.py).**

---

### `INFERENCE_PIPELINE_WRAPPER`

**Description:**
Wraps an existing inference pipeline with `hailocropper` and `hailoaggregator` elements. This wrapper maintains the original video resolution and color space, ensuring seamless integration with complex pipelines.

**Usage:**
Use the `INFERENCE_PIPELINE_WRAPPER` function to encapsulate your inference pipeline, facilitating advanced processing like cropping and aggregation without altering the original pipeline's properties.
**Note:** The post process will have to warp the network output to the 'original' resolution. This is not yet implemented in all post processes and metadata types.

**For more details, refer to the [`INFERENCE_PIPELINE_WRAPPER` function in `gstreamer_helper_pipelines.py`](hailo_apps_infra/gstreamer_helper_pipelines.py).**

---

### `QUEUE`

**Description:**
Creates a GStreamer `queue` element with configurable parameters. Queues are essential for managing the flow of data between different pipeline elements, ensuring smooth and efficient processing.It is also used to enable multithreading. A queue will create a new thread on its output, allowing different parts of the pipeline to run in parallel. See [Gstreamer Multithreading documentation](https://gstreamer.freedesktop.org/documentation/tutorials/basic/handy-elements.html#multithreading) for more details.

**Usage:**
Use the `QUEUE` function to insert buffering points in your pipeline, controlling the number of buffers, bytes, and time the queue can handle, as well as its leak behavior.

**For more details, refer to the [`QUEUE` function in `gstreamer_helper_pipelines.py`](hailo_apps_infra/gstreamer_helper_pipelines.py).**

### `TRACKER_PIPELINE`
**Description:**
Wraps an inner pipeline with hailocropper and hailoaggregator.
The cropper will crop detections made by earlier stages in the pipeline.
Each detection is cropped and sent to the inner pipeline for further processing.
The aggregator will combine the cropped detections with the original frame.
Example use case: After face detection pipeline stage, crop the faces and send them to a face recognition pipeline.

**Usage:**
Use the `TRACKER_PIPELINE` function to add a tracker stage to your pipeline for tracking detections.

**For more details, refer to the [`TRACKER_PIPELINE` function in `gstreamer_helper_pipelines.py`](hailo_apps_infra/gstreamer_helper_pipelines.py).**

---

### `DISPLAY_PIPELINE`

**Description:**
Generates a GStreamer pipeline string for displaying video output. Incorporates the `hailooverlay` plugin to render bounding boxes and labels, enhancing the visual output of processed frames.

**Usage:**
Utilize the `DISPLAY_PIPELINE` function to add a display segment to your pipeline, with options to enable FPS overlay and configure the video sink.

**For more details, refer to the [`DISPLAY_PIPELINE` function in `gstreamer_helper_pipelines.py`](hailo_apps_infra/gstreamer_helper_pipelines.py).**

---

### `USER_CALLBACK_PIPELINE`

**Description:**
Creates a GStreamer pipeline string for integrating a user-defined callback element. This allows developers to inject custom processing logic at specific points within the pipeline.

**Usage:**
Use the `USER_CALLBACK_PIPELINE` function to add a callback stage to your pipeline, enabling custom data handling and processing as needed.

**For more details, refer to the [`USER_CALLBACK_PIPELINE` function in `gstreamer_helper_pipelines.py`](hailo_apps_infra/gstreamer_helper_pipelines.py).**

### `CROPPER_PIPELINE`
**Description:**
Wraps an inner pipeline with hailocropper and hailoaggregator.
The cropper will crop detections made by earlier stages in the pipeline.
Each detection is cropped and sent to the inner pipeline for further processing.
The aggregator will combine the cropped detections with the original frame.
Example use case: After face detection pipeline stage, crop the faces and send them to a face recognition pipeline.

**Usage:**
Use the `CROPPER_PIPELINE` function to add a cropper stage to your pipeline, enabling cascading detections to the next network.

**For more details, refer to the [`CROPPER_PIPELINE` function in `gstreamer_helper_pipelines.py`](hailo_apps_infra/gstreamer_helper_pipelines.py).**

### `FILE_SINK_PIPELINE`

**Description:**
Creates a GStreamer pipeline string for saving video output to a file in `.mkv` format. This function is useful for recording the processed video stream to a file for later analysis or playback.
Note: If your source is a file, looping will not work with this pipeline.

**Key Features:**
- **Video Conversion:** Converts the video to a suitable format for encoding.
- **Encoding:** Encodes the video using the `x264enc` encoder with a specified bitrate.
- **Muxing:** Muxes the encoded video into a Matroska (`.mkv`) container.
- **File Output:** Saves the muxed video to a specified file location.

**Usage:**
To use the `FILE_SINK_PIPELINE` function, integrate it into your GStreamer pipeline. Below is an example of how to use this function in a custom GStreamer application.

**Post-Processing:**
After recording the video, it is recommended to run `ffmpeg` to fix the file header. This step ensures that the recorded video file is properly formatted and playable.
```bash
ffmpeg -i output.mkv -c copy fixed_output.mkv
```

**For more details, refer to the [`FILE_SINK_PIPELINE` function in `gstreamer_helper_pipelines.py`](hailo_apps_infra/gstreamer_helper_pipelines.py).**


## Running with Different Input Sources
By default, pipelines will use an example video source. You can change the input source using the `--input` flag.

### File Input
To use file input, use the file's path for example run the following command:
```bash
python hailo_apps_infra/detection_pipeline.py --input resources/example.mp4
```

### Raspberry Pi Camera Input
To use the Raspberry Pi camera input, use the `rpi` source for example run the following command:
```bash
python hailo_apps_infra/detection_pipeline.py --input rpi
```
This will work on Raspberry Pi's with the camera module connected.

### USB Camera Input
To determine which USB camera to use, please run the following script:
```bash
get-usb-camera
```
This will help you identify an available camera.
Use the camera's index as the input source. For example, to use `/dev/video0`, replace `/dev/video<X>` and run the following command:
```bash
python hailo_apps_infra/detection_pipeline.py --input /dev/video<X>
```

#### Ximage video source
Allows you to use a window as a video source.
This input is not compatible with Raspberry Pi (RPi), at least according to our tests.

In a terminal run:
```bash
xwininfo
```
If it is not installed, install it with:
```bash
sudo apt install x11-utils
```

You will get a message to select a window. Click on the window you want to use as a video source.
You should get an output like this:
```bash
xwininfo

xwininfo: Please select the window about which you
          would like information by clicking the
          mouse in that window.

xwininfo: Window id: 0x3600004 "New Tab - Google Chrome"

  Absolute upper-left X:  70
  Absolute upper-left Y:  1107
  Relative upper-left X:  70
  Relative upper-left Y:  1107
  Width: 1850
  Height: 1053
  Depth: 32
  Visual: 0x8ec
  Visual Class: TrueColor
  Border width: 0
  Class: InputOutput
  Colormap: 0x3600003 (not installed)
  Bit Gravity State: NorthWestGravity
  Window Gravity State: NorthWestGravity
  Backing Store State: NotUseful
  Save Under State: no
  Map State: IsViewable
  Override Redirect State: no
  Corners:  +70+1107  -0+1107  -0-0  +70-0
  -geometry 1850x1053-0-0
```
The window id is `0x3600004` in this case.
Run the following command:
```bash
python hailo_apps_infra/detection_pipeline.py --input <window id>
```

#### File input
```bash
python hailo_apps_infra/detection_pipeline.py  --input resources/example.mp4
```

### Using the Frame Buffer
To utilize the frame buffer, add the `--use-frame` flag. Be aware that extracting and displaying video frames can slow down the application due to non-optimized implementation. Writing to the buffer and replacing the old buffer in the pipeline is possible but inefficient.

### Printing the Frame Rate
To display the frame rate, add the `--show-fps` flag. This will print the FPS to both the terminal and the video output window.

### Dumping the Pipeline Graph
Useful for debugging and understanding the pipeline structure. To dump the pipeline graph to a DOT file, add the `--dump-dot` flag:
```bash
python hailo_apps_infra/detection_pipeline.py  --dump-dot
```
This creates a file named `pipeline.dot` in the `hailo_apps_infra` directory.

**Visualize the pipeline using Graphviz:**
1. **Install Graphviz:**
    ```bash
    sudo apt install graphviz
    ```
2. **Visualize the pipeline:**
    ```bash
    dot -Tx11 hailo_apps_infra/pipeline.dot &
    ```
3. **Save the pipeline as a PNG:**
    ```bash
    dot -Tpng hailo_apps_infra/pipeline.dot -o pipeline.png
    ```

# Troubleshooting and Known Issues
If you encounter any issues, please open a ticket in the [Hailo Community Forum](https://community.hailo.ai/). The forum is a valuable resource filled with useful information and potential solutions.

**Known Issues:**
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
