import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import numpy as np
import cv2
import hailo
from hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from instance_segmentation_pipeline import GStreamerInstanceSegmentationApp

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------

# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK

    # Using the user_data to count the number of frames
    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"

    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)

    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        # Get video frame
        frame = get_numpy_from_buffer(buffer, format, width, height)

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Parse the detections
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
        if label == "person":
            string_to_print += (f"Detection: {label} {confidence:.2f}\n")
            if user_data.use_frame:
                # Instance segmentation mask from detection (if available)
                masks = detection.get_objects_typed(hailo.HAILO_CONF_CLASS_MASK)
                if len(masks) != 0:
                    mask = masks[0]
                    # Note that the mask is a 1D array, you need to reshape it to get the original shape
                    mask_height = mask.get_height()
                    mask_width = mask.get_width()
                    data = np.array(mask.get_data())
                    data = data.reshape((mask_height, mask_width))
                    # data should be enlarged x4
                    mask_width = mask_width * 4
                    mask_height = mask_height * 4
                    data = cv2.resize(data, (mask_width, mask_height), interpolation=cv2.INTER_NEAREST)
                    string_to_print += f"Mask shape: {data.shape}, "
                    string_to_print += f"Base coordinates ({int(bbox.xmin() * width)},{int(bbox.ymin() * height)})\n"

                    # This code is on remark due to performance issues
                    # # Add mask overlay to the frame
                    # mask_overlay = np.zeros_like(frame)
                    # x_min, y_min = int(bbox.xmin() * width), int(bbox.ymin() * height)
                    # x_max, y_max = x_min + mask_width, y_min + mask_height
                    # mask_overlay[y_min:y_max, x_min:x_max, 2] = (data > 0.5) * 255  # Red channel
                    # frame = cv2.addWeighted(frame, 1, mask_overlay, 0.5, 0)

    print(string_to_print)

    if user_data.use_frame:
        # Convert the frame to BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    app = GStreamerInstanceSegmentationApp(app_callback, user_data)
    app.run()
