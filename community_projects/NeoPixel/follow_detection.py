import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import sys
import numpy as np
import cv2
import hailo
sys.path.append('../../basic_pipelines')

from hailo_apps.hailo_app_python.core.common.buffer_utils import get_caps_from_pad, get_numpy_from_buffer
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.hailo_app_python.apps.detection.detection_pipeline import GStreamerDetectionApp

# Based on https://github.com/vanshksingh/Pi5Neo
# Pins connections:
# Connect 5+ to 5V
# GND to GND
# Din to GPIO10 (SPI MOSI)

# install using 'pip install pi5neo'
from pi5neo import Pi5Neo

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.num_leds = 10
        self.neo = Pi5Neo('/dev/spidev0.0', self.num_leds, 800)
        self.update_rate = 4
# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------

# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    # Using the user_data to count the number of frames
    user_data.increment()
    # run only every user_data.update_rate frames
    if (user_data.get_count() % user_data.update_rate):
        return Gst.PadProbeReturn.OK
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Parse the detections
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
        if label == "person":
            # control leds according to person X location
            x = (bbox.xmin() + bbox.xmax()) / 2
            # select led to light
            ind = int(user_data.num_leds * x)
            print(f'setting led {ind}')
            user_data.neo.fill_strip(0, 0, 0) # clear all leds
            user_data.neo.set_led_color(ind, 0, 0, 255)
            user_data.neo.update_strip()
            # exit after first detection
            return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()
