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
import math
import json

# Load configuration from config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Load CLASS_* options from config
CLASS_DETECTED_COUNT = config.get('CLASS_DETECTED_COUNT', 4)
CLASS_GONE_COUNT = config.get('CLASS_GONE_COUNT', 12)
CLASS_MATCH_CONFIDENCE = config.get('CLASS_MATCH_CONFIDENCE', 0.4)
CLASS_TO_TRACK = config.get('CLASS_TO_TRACK', 'dog')
ALIAS_CLASSES_TO_ALLOW = config.get('ALIAS_CLASSES_TO_ALLOW', [])
SAVE_DETECTION_IMAGES = config.get('SAVE_DETECTION_IMAGES', True)
SHOW_DETECTION_BOXES = config.get('SHOW_DETECTION_BOXES', True)
SAVE_DETECTION_VIDEO = config.get('SAVE_DETECTION_VIDEO', False)

class Point2D:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point2D({self.x}, {self.y})"

    def round(self, n=2):
        return Point2D(round(self.x, n), round(self.y, n))

    def subtract(self, p):
        return Point2D(self.x - p.x, self.y - p.y)

    def magnitude(self):
        return (self.x**2 + self.y**2)**0.5

    def direction(self):
        angle = math.degrees(math.atan2(self.y, self.x))
        return angle if angle >= 0 else angle + 360

# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        
        # Initialize state variables for debouncing
        self.detection_counter = 0  # Count consecutive frames with detections
        self.no_detection_counter = 0  # Count consecutive frames without detections
        self.max_instances = 0  # Maximum number of instances detected in a frame
        self.object_centroid = None  # Current object centroid
        self.start_centroid = None  # Start centroid when object is first detected
        self.end_centroid = None  # End centroid when object is gone
        
        # State tracking, is the debounced object active or not?
        self.is_active_tracking = False

        # Variables for computing average detection instance count
        self.total_detection_instances = 0
        self.active_detection_count = 0

        # Setup speech file
        # make request to google to get synthesis
        tts = gtts.gTTS(f"Its a {CLASS_TO_TRACK.upper()}")
        # save the audio file
        tts.save("alert.mp3")

        print(f"Looking for {CLASS_TO_TRACK.upper()}")

        # Initialize video writer
        self.video_writer = None
        self.video_filename = None

        self.format = None
        self.width = None
        self.height = None

    def start_video_recording(self, width, height, video_filename):
        self.video_filename = video_filename
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(video_filename, fourcc, 20.0, (width, height))

    def write_video_frame(self, frame):
        if self.video_writer is not None and self.current_frame is not None:
            self.video_writer.write(frame)

    def draw_detection_boxes(self, detections, width, height):
        if self.current_frame is not None and SHOW_DETECTION_BOXES:
            for detection in detections:
                bbox = detection.get_bbox()
                cv2.rectangle(self.current_frame, 
                              (int(bbox.xmin() * width), int(bbox.ymin() * height)), 
                              (int(bbox.xmax() * width), int(bbox.ymax() * height)), 
                              (0, 0, 255), 1)

    def stop_video_recording(self, final_filename):
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            os.rename(self.video_filename, final_filename)
            print(f"Video saved as {final_filename}")
     
    def get_average_detection_instance_count(self):
        if self.active_detection_count == 0:
            return 0
        return self.total_detection_instances / self.active_detection_count

    def start_active_tracking(self, class_detections):
        self.is_active_tracking = True
        self.max_instances = len(class_detections)
        self.start_centroid = self.object_centroid
        self.start_area = self.object_area
        self.save_frame = self.current_frame
        self.active_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

        # Draw detection boxes on the frame if SHOW_DETECTION_BOXES is True
        if self.current_frame is not None and SHOW_DETECTION_BOXES:
            self.draw_detection_boxes(class_detections, self.width, self.height)

        # Start recording video if SAVE_DETECTION_VIDEO and self.video_writer is None and frame is not None:
        if SAVE_DETECTION_VIDEO and self.video_writer is None and self.current_frame is not None:
            video_dir = f"videos/{CLASS_TO_TRACK}"
            os.makedirs(video_dir, exist_ok=True)
            video_filename = f"{video_dir}/{self.active_timestamp}_{CLASS_TO_TRACK}.mp4"
            self.start_video_recording(self.width, self.height, video_filename)

        phrase = f"{CLASS_TO_TRACK.upper()} DETECTED"
        print(f"{phrase} {self.start_centroid} at: {datetime.datetime.now()}")
        playsound("alert.mp3", 0)

    def active_tracking(self, class_detections):
        # If a frame is available, write the frame to the video
        if self.current_frame is not None:
            self.write_video_frame(self.current_frame)

        # Update total detection instances and active detection count for later averaging
        detection_instance_count = len(class_detections)
        if detection_instance_count > 0:
            # Draw detection boxes on the frame if SHOW_DETECTION_BOXES is True
            if SHOW_DETECTION_BOXES:
                self.draw_detection_boxes(class_detections, self.width, self.height)
            self.total_detection_instances += detection_instance_count
            self.active_detection_count += 1
            if detection_instance_count > self.max_instances:
                self.max_instances = detection_instance_count
                self.save_frame = self.detection_frame

    def stop_active_tracking(self):
        
        self.is_active_tracking = False
        self.end_centroid = self.object_centroid
        self.end_area = self.object_area

        if self.start_centroid is not None:
            direction = self.end_centroid.subtract(self.start_centroid).direction()
        else:
            direction = None
        avg_detection_count = self.get_average_detection_instance_count()
        print(f"{CLASS_TO_TRACK.upper()} GONE at: {self.end_centroid} time: {datetime.datetime.now()}, area: {self.end_area:.3f}, direction: {direction:.0f} degrees, avg count: {avg_detection_count:.2f}, max count: {self.max_instances}")

        # Stop any video recording and rename the file to include the average count
        final_filename = f"videos/{CLASS_TO_TRACK}/{self.active_timestamp}_{CLASS_TO_TRACK}_x{self.max_instances}({avg_detection_count:.2f})_{direction:.0f}).mp4"
        self.stop_video_recording(final_filename)

        # Save the frame with the most instances if SAVE_DETECTION_IMAGES is True
        if self.save_frame is not None and SAVE_DETECTION_IMAGES:
            self.image_filename = f"images/{CLASS_TO_TRACK}/{self.active_timestamp}_{CLASS_TO_TRACK}_x{self.max_instances}({avg_detection_count:.2f})_{direction:.0f}.jpg"
            cv2.imwrite(self.image_filename, self.save_frame)
            print(f"Image saved as {self.image_filename}")

        self.max_instances = 0
        self.save_frame = None
        self.object_centroid = None
        self.object_area = None

    def get_avg_centroid(self, class_detections):
        """
        Calculate the average centroid of a list of class detections.
        Args:
            class_detections (list): A list of detection objects, each containing a bounding box.
        Returns:
            Point2D: The average centroid point of the given detections.
        Raises:
            ValueError: If class_detections is empty.
        """
        centroids = []
        for detection in class_detections:
            bbox = detection.get_bbox()
            centroid_x = (bbox.xmin() + bbox.xmax()) / 2
            centroid_y = (bbox.ymin() + bbox.ymax()) / 2
            centroids.append(Point2D(centroid_x, centroid_y))
            
        if len(centroids):
            avg_centroid_x = sum(point.x for point in centroids) / len(centroids)
            avg_centroid_y = sum(point.y for point in centroids) / len(centroids)

        return Point2D(avg_centroid_x, avg_centroid_y)

    def get_total_bbox_area(self, class_detections):
        """
        Calculate the total area of all bounding boxes in a list of class detections.
        Args:
            class_detections (list): A list of detection objects, each containing a bounding box.
        Returns:
            float: The total area of all bounding boxes.
        """
        total_area = 0.0
        for detection in class_detections:
            bbox = detection.get_bbox()
            width = bbox.xmax() - bbox.xmin()
            height = bbox.ymax() - bbox.ymin()
            total_area += width * height
        return total_area


def app_callback(pad, info, user_data):
    """
    Callback function for processing video frames and detecting objects.
    Args:
        pad (Gst.Pad): The pad from which the buffer is received.
        info (Gst.PadProbeInfo): The probe info containing the buffer.
        user_data (UserData): Custom user data object for tracking state and configurations.
    Returns:
        Gst.PadProbeReturn: Indicates the result of the pad probe.
    The function performs the following tasks:
    - Retrieves the GstBuffer from the probe info.
    - Increments the frame count using user_data.
    - Extracts video frame information if user_data.use_frame is True.
    - Retrieves detections from the buffer and filters them based on class and confidence.
    - Counts the number of filtered detections.
    - Implements debouncing logic to determine if an object is detected or not.
    - Activates or deactivates detection state based on consecutive frames with or without detections.
    - Logs detection events and saves frame images when an object is detected.
    """
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK
    
    # Using the user_data to count the number of frames
    user_data.increment()
    
    # Get the caps from the pad
    user_data.format, user_data.width, user_data.height = get_caps_from_pad(pad)
    
    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    if user_data.use_frame and user_data.format is not None and user_data.width is not None and user_data.height is not None:
        user_data.current_frame = get_numpy_from_buffer(buffer, user_data.format, user_data.width, user_data.height)
        user_data.current_frame = cv2.cvtColor(user_data.current_frame, cv2.COLOR_RGB2BGR)
    
    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Filter detections that match CLASS_TO_TRACK or ALIAS_CLASSES_TO_ALLOW and have confidence greater than CLASS_MATCH_CONFIDENCE
    class_detections = [
        detection for detection in detections if (detection.get_label() == CLASS_TO_TRACK or detection.get_label() in ALIAS_CLASSES_TO_ALLOW) and detection.get_confidence() > CLASS_MATCH_CONFIDENCE
    ]

    # Count the number of detections that match CLASS_TO_TRACK or ALIAS_CLASSES_TO_ALLOW and have confidence greater than CLASS_MATCH_CONFIDENCE
    detection_instance_count = len(class_detections)
    object_detected = False
    if detection_instance_count > 0:
        object_detected = True
        user_data.object_centroid = user_data.get_avg_centroid(class_detections).round()
        user_data.object_area = user_data.get_total_bbox_area(class_detections)
        user_data.detection_frame = user_data.current_frame

    # Debouncing logic to start/stop active tracking
    if object_detected:
        user_data.detection_counter += 1
        user_data.no_detection_counter = 0
        
        # Only activate after CLASS_DETECTED_COUNT consecutive frames with detections
        if user_data.detection_counter >= CLASS_DETECTED_COUNT and not user_data.is_active_tracking:
            user_data.start_active_tracking(class_detections)
    else:
        user_data.no_detection_counter += 1
        user_data.detection_counter = 0
        
        # Only deactivate after CLASS_GONE_COUNT consecutive frames without detections
        if user_data.no_detection_counter >= CLASS_GONE_COUNT and user_data.is_active_tracking:
            user_data.stop_active_tracking()

    # Active tracking
    if user_data.is_active_tracking:
        user_data.active_tracking(class_detections)

    return Gst.PadProbeReturn.OK

if __name__ == "__main__":

    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()