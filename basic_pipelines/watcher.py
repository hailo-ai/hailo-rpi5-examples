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

CLASS_TO_TRACK = "dog"
CLASS_DETECTED_COUNT = 4
CLASS_GONE_COUNT = 8

# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        
        # Initialize state variables for debouncing
        self.detection_counter = 0  # Count consecutive frames with detections
        self.no_detection_counter = 0  # Count consecutive frames without detections
        
        # State tracking, is it active or not?
        self.is_it_active = False

        # Setup speech file
        # make request to google to get synthesis
        tts = gtts.gTTS(f"Its a {CLASS_TO_TRACK.upper()}")
        # save the audio file
        tts.save("alert.mp3")
     

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
    
    # Track if we've seen objects of interest this frame
    object_detected = False
    detection_string = ""
    
    # Parse the detections
    for detection in detections:
        label = detection.get_label()
        confidence = detection.get_confidence()
        
        # Check for objects of interest with confidence threshold
        if confidence > 0.4:  # Adjust confidence threshold as needed
            if label == CLASS_TO_TRACK:
                object_detected = True
                detection_string += f"Detection: {label} {confidence:.2f}\n"

    # Debouncing logic
    if object_detected:
        user_data.detection_counter += 1
        user_data.no_detection_counter = 0
        
        # Only activate after given amount of consecutive frames with detections
        if user_data.detection_counter >= CLASS_DETECTED_COUNT and not user_data.is_it_active:
            # Update the is it active variable so this doesnt keep repeating
            user_data.is_it_active = True

            phrase = f"{CLASS_TO_TRACK.upper()} DETECTED!"
            print(f"{phrase} at: {datetime.datetime.now()}")
            
            playsound("alert.mp3",0)
    else:
        user_data.no_detection_counter += 1
        user_data.detection_counter = 0
        
        # Only deactivate after N consecutive frames without detections
        if user_data.no_detection_counter >= CLASS_GONE_COUNT and user_data.is_it_active:
            user_data.is_it_active = False
            print(f"{CLASS_TO_TRACK.upper()} Gone at: {datetime.datetime.now()}")

    # Print detections if any
    #if detection_string:
    #    print(detection_string, end='')
    
    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    app = GStreamerDetectionApp(app_callback, user_data)
    app.run()