import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import sys
import numpy as np
import cv2
import hailo

from hailo_apps.hailo_app_python.core.common.buffer_utils import get_caps_from_pad
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.hailo_app_python.apps.pose_estimation.pose_estimation_pipeline import GStreamerPoseEstimationApp
from hailo_apps.hailo_app_python.core.common.core import get_default_parser

from wled_display import WLEDDisplay, add_parser_args

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self, parser):
        super().__init__()
        self.wled = WLEDDisplay(parser=parser)
        self.frame_skip = 2  # Process every 2nd frame

# Predefined colors (BGR format)
COLORS = [
    (255, 0, 0),    # Red
    (0, 255, 0),    # Green
    (0, 0, 255),    # Blue
    (255, 255, 0),  # Cyan
    (255, 0, 255),  # Magenta
    (0, 255, 255),  # Yellow
    (128, 0, 128),  # Purple
    (255, 165, 0),  # Orange
    (0, 128, 128),  # Teal
    (128, 128, 0)   # Olive
]

CONFIDENCE_THRESHOLD = 0.5 # Confidence threshold for keypoints

# Keypoints for pose estimation (example indices, adjust based on your model)
keypoints = {
    'nose': 0,
    'left_eye': 1,
    'right_eye': 2,
    'left_ear': 3,
    'right_ear': 4,
    'left_shoulder': 5,
    'right_shoulder': 6,
    'left_elbow': 7,
    'right_elbow': 8,
    'left_wrist': 9,
    'right_wrist': 10,
    'left_hip': 11,
    'right_hip': 12,
    'left_knee': 13,
    'right_knee': 14,
    'left_ankle': 15,
    'right_ankle': 16
}

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------

# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    # Using the user_data to count the number of frames
    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"

    # Skip frames to reduce compute
    if user_data.get_count() % user_data.frame_skip != 0:
        return Gst.PadProbeReturn.OK

    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK

    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)

    # Reduce the resolution by a factor of 4
    reduced_width = width // 4
    reduced_height = height // 4

    # Generate a zero-filled numpy array for the reduced frame
    reduced_frame = np.zeros((reduced_height, reduced_width, 3), dtype=np.uint8)

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
            # Get track ID
            track_id = 0
            track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
            if len(track) == 1:
                track_id = track[0].get_id()

            # Pose estimation landmarks from detection (if available)
            landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
            if len(landmarks) != 0:
                points = landmarks[0].get_points()
                for wrist in ['left_wrist', 'right_wrist']:
                    keypoint_index = keypoints[wrist]
                    point = points[keypoint_index]
                    if point.confidence() < CONFIDENCE_THRESHOLD:
                        continue
                    x = int((point.x() * bbox.width() + bbox.xmin()) * reduced_width)
                    y = int((point.y() * bbox.height() + bbox.ymin()) * reduced_height)
                    string_to_print += f"{wrist}: x: {x:.2f} y: {y:.2f}\n"
                    color = COLORS[track_id % len(COLORS)]  # Get color based on track_id
                    cv2.circle(reduced_frame, (x, y), 10, color, -1)

    # Resize the frame to the WLED size for display
    final_frame = cv2.resize(reduced_frame, (user_data.wled.width, user_data.wled.height))
    user_data.wled.frame_queue.put(final_frame)

    print(string_to_print)
    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    # Create a modified parser to include WLED display options
    parser = get_default_parser()
    # Add WLED display options
    add_parser_args(parser)
    # Create an instance of the user app callback class
    user_data = user_app_callback_class(parser)
    app = GStreamerPoseEstimationApp(app_callback, user_data, parser)
    app.run()