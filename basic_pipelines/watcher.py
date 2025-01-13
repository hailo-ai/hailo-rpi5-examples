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
from detection_pipeline import GStreamerDetectionApp

import gtts
from playsound import playsound
import datetime
import argparse

CLASS_DETECTED_COUNT = 4
CLASS_GONE_COUNT = 8
CLASS_MATCH_CONFIDENCE = 0.4

def parse_args():
    parser = argparse.ArgumentParser(description="Object Detection Watcher")
    parser.add_argument(
        "--class-to-track", "-c", type=str, default="car",
        help="Class to track. Defaults to 'car'."
    )
    return parser.parse_known_args()[0]

# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        
        # Initialize state variables for debouncing
        self.detection_counter = 0  # Count consecutive frames with detections
        self.no_detection_counter = 0  # Count consecutive frames without detections
        self.max_instances = 0  # Maximum number of instances detected in a frame
        
        # State tracking, is it active or not?
        self.is_it_active = False

        # Parse class to track arg
        args = parse_args()
        self.class_to_track = args.class_to_track

        # Setup speech file
        # make request to google to get synthesis
        tts = gtts.gTTS(f"Its a {self.class_to_track.upper()}")
        # save the audio file
        tts.save("alert.mp3")

        print(f"Looking for {self.class_to_track.upper()}")
     

def app_callback(pad, info, user_data):
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK
    
    # Using the user_data to count the number of frames
    user_data.increment()
    
    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)
    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        frame = get_numpy_from_buffer(buffer, format, width, height)
    
    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Filter detections that match class_to_track and have confidence greater than CLASS_MATCH_CONFIDENCE
    class_detections = [
        detection for detection in detections if detection.get_label() == user_data.class_to_track and detection.get_confidence() > CLASS_MATCH_CONFIDENCE
    ]

    # Count the number of detections that match class_to_track and have confidence greater than CLASS_MATCH_CONFIDENCE
    detection_instance_count = len(class_detections)
    object_detected = False
    if detection_instance_count > 0:
        object_detected = True
        user_data.object_centroid= get_avg_centroid(class_detections)

    # Debouncing logic
    if object_detected:
        user_data.detection_counter += 1
        user_data.no_detection_counter = 0
        
        # Only activate after given amount of consecutive frames with detections
        if user_data.detection_counter >= CLASS_DETECTED_COUNT and not user_data.is_it_active:
            # Update the is it active variable so this doesnt keep repeating
            user_data.is_it_active = True
            user_data.max_instances = 0
            user_data.start_centroid = user_data.object_centroid
            phrase = f"{user_data.class_to_track.upper()} DETECTED!"
            print(f"{phrase} {user_data.start_centroid} at: {datetime.datetime.now()}")         
            playsound("alert.mp3",0)
    else:
        user_data.no_detection_counter += 1
        user_data.detection_counter = 0
        
        # Only deactivate after N consecutive frames without detections
        if user_data.no_detection_counter >= CLASS_GONE_COUNT and user_data.is_it_active:
            user_data.is_it_active = False
            user_data.max_instances = 0
            user_data.end_centroid = user_data.object_centroid
            print(f"{user_data.class_to_track.upper()} Gone at: {user_data.end_centroid} time: {datetime.datetime.now()}")

    if user_data.is_it_active:
        # It's possible that the number of instances detected in a frame is greater than the previous value
        if detection_instance_count > user_data.max_instances:
            user_data.max_instances = detection_instance_count
            print(f"{user_data.class_to_track.upper()} count is {user_data.max_instances}")

            # Save the current frame image
            if frame is not None:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                class_to_track = user_data.class_to_track
                os.makedirs(f"images/{class_to_track}", exist_ok=True)
                cv2.imwrite(f"images/{class_to_track}/{timestamp}_{user_data.class_to_track}x{detection_instance_count}.jpg", frame)

    
    return Gst.PadProbeReturn.OK

def get_avg_centroid(class_detections):
    centroids = []
    for detection in class_detections:
        bbox = detection.get_bbox()
        centroid_x = (bbox.xmin() + bbox.xmax()) / 2
        centroid_y = (bbox.ymin() + bbox.ymax()) / 2
        centroids.append((centroid_x, centroid_y))
        
    if len(centroids):
        avg_centroid_x = sum(x for x, y in centroids) / len(centroids)
        avg_centroid_y = sum(y for x, y in centroids) / len(centroids)

    return (avg_centroid_x, avg_centroid_y)

if __name__ == "__main__":

    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()