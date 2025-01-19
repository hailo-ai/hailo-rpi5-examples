import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject
import os
import argparse
import multiprocessing
import numpy as np
import setproctitle
import cv2
import time
import signal
import threading
import subprocess
from hailo_apps_infra.gstreamer_app import (
    app_callback_class
)

# Try to import hailo python module
try:
    import hailo
except ImportError:
    sys.exit("Failed to import hailo python module. Make sure you are in hailo virtual environment.")

# -----------------------------------------------------------------------------------------------
# Common functions
# -----------------------------------------------------------------------------------------------
def detect_hailo_arch():
    try:
        # Run the hailortcli command to get device information
        result = subprocess.run(['hailortcli', 'fw-control', 'identify'], capture_output=True, text=True)

        # Check if the command was successful
        if result.returncode != 0:
            print(f"Error running hailortcli: {result.stderr}")
            return None

        # Search for the "Device Architecture" line in the output
        for line in result.stdout.split('\n'):
            if "Device Architecture" in line:
                if "HAILO8L" in line:
                    return "hailo8l"
                elif "HAILO8" in line:
                    return "hailo8"

        print("Could not determine Hailo architecture from device information.")
        return None
    except Exception as e:
        print(f"An error occurred while detecting Hailo architecture: {e}")
        return None

def get_caps_from_pad(pad: Gst.Pad):
    caps = pad.get_current_caps()
    if caps:
        # We can now extract information from the caps
        structure = caps.get_structure(0)
        if structure:
            # Extracting some common properties
            format = structure.get_value('format')
            width = structure.get_value('width')
            height = structure.get_value('height')
            return format, width, height
    else:
        return None, None, None


def get_default_parser():
    parser = argparse.ArgumentParser(description="Hailo App Help")
    current_path = os.path.dirname(os.path.abspath(__file__))
    default_video_source = os.path.join(current_path, '../resources/example.mp4')
    parser.add_argument(
        "--input", "-i", type=str, default=default_video_source,
        help="Input source. Can be a file, USB (webcam), RPi camera (CSI camera module) or ximage. \
        For RPi camera use '-i rpi' \
        Defaults to example video resources/example.mp4"
    )
    parser.add_argument("--use-frame", "-u", action="store_true", help="Use frame from the callback function")
    parser.add_argument("--show-fps", "-f", action="store_true", help="Print FPS on sink")
    parser.add_argument(
            "--arch",
            default=None,
            choices=['hailo8', 'hailo8l'],
            help="Specify the Hailo architecture (hailo8 or hailo8l). Default is None , app will run check.",
        )
    parser.add_argument(
            "--hef-path",
            default=None,
            help="Path to HEF file",
        )
    parser.add_argument(
        "--disable-sync", action="store_true",
        help="Disables display sink sync, will run as fast as possible. Relevant when using file source."
    )
    parser.add_argument("--dump-dot", action="store_true", help="Dump the pipeline graph to a dot file pipeline.dot")
    return parser


# ---------------------------------------------------------
# Functions used to get numpy arrays from GStreamer buffers
# ---------------------------------------------------------

def handle_rgb(map_info, width, height):
    # The copy() method is used to create a copy of the numpy array. This is necessary because the original numpy array is created from buffer data, and it does not own the data it represents. Instead, it's just a view of the buffer's data.
    return np.ndarray(shape=(height, width, 3), dtype=np.uint8, buffer=map_info.data).copy()

def handle_nv12(map_info, width, height):
    y_plane_size = width * height
    uv_plane_size = width * height // 2
    y_plane = np.ndarray(shape=(height, width), dtype=np.uint8, buffer=map_info.data[:y_plane_size]).copy()
    uv_plane = np.ndarray(shape=(height//2, width//2, 2), dtype=np.uint8, buffer=map_info.data[y_plane_size:]).copy()
    return y_plane, uv_plane

def handle_yuyv(map_info, width, height):
    return np.ndarray(shape=(height, width, 2), dtype=np.uint8, buffer=map_info.data).copy()

FORMAT_HANDLERS = {
    'RGB': handle_rgb,
    'NV12': handle_nv12,
    'YUYV': handle_yuyv,
}

def get_numpy_from_buffer(buffer, format, width, height):
    """
    Converts a GstBuffer to a numpy array based on provided format, width, and height.

    Args:
        buffer (GstBuffer): The GStreamer Buffer to convert.
        format (str): The video format ('RGB', 'NV12', 'YUYV', etc.).
        width (int): The width of the video frame.
        height (int): The height of the video frame.

    Returns:
        np.ndarray: A numpy array representing the buffer's data, or a tuple of arrays for certain formats.
    """
    # Map the buffer to access data
    success, map_info = buffer.map(Gst.MapFlags.READ)
    if not success:
        raise ValueError("Buffer mapping failed")

    try:
        # Handle different formats based on the provided format parameter
        handler = FORMAT_HANDLERS.get(format)
        if handler is None:
            raise ValueError(f"Unsupported format: {format}")
        return handler(map_info, width, height)
    finally:
        buffer.unmap(map_info)
