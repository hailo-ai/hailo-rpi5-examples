import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import numpy as np
import cv2
import hailo
from enum import Enum
from playsound import playsound
import time
import threading
import random
import argparse
from treat_control import treat_control
try:
    from arm_control import arm_control
except :
    pass

from collections import Counter

from hailo_apps.hailo_app_python.core.common.buffer_utils import get_caps_from_pad, get_numpy_from_buffer
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.hailo_app_python.apps.detection.detection_pipeline import GStreamerDetectionApp
from hailo_apps.hailo_app_python.core.common.core import get_default_parser



class Pet_State(Enum):    
    PET_IDLE = 0
    PET_HOMING = 1
    PET_NOT_CENTERED = 2
    PET_ON_COUCH = 3
    PET_LOCKED = 4

SEC = 30 #FPS
WARN_DURATION = 0
SHOOT_DURATION = 10
EVENTS_SIZE = 60 # "remember" 60 events for getting current event calc

events = []
cooldown_period = 0

angle = 90
sign = 1

cur_event = None

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.warning_files = [
            'warn_pet1.mp3',
            'warn_pet2.mp3',
            'warn_pet3.mp3',
        ]
        self.treat_files = [
            'treat_pet1.mp3'
        ]


    def get_timestamp(self):
        return (round(time.time()))

    def punish_pet(self):
        print ("Punish pet")
        #TODO: move treat to treat events

    def play_sound_in_background(self, file_path):
        """
        Plays an audio file in the background using playsound.
        
        Args:
            file_path (str): Path to the audio file to play.
        """
        threading.Thread(target=playsound, args=(file_path,), daemon=True).start()

    def treat_pet(self):
        print ("Treat dog")
        random_file = random.choice(self.treat_files)
        print(random_file)
        self.play_sound_in_background(f"./resources/{random_file}")
        treat_control.perform_treat_throw()

    def scan_pet(self):
        global angle
        global sign
        print ("Scanning dog")
        step = sign * 1
        angle += step
        print(angle)
        if not app.options_menu.no_arm_control:
            arm_control.set_arm_horizontal_angle(angle)
        if  angle>= 150 or angle <=30:
            sign *=-1

    def warn_pet(self):
        print ("Warning dog")
        random_file = random.choice(self.warning_files)
        print(random_file)
        self.play_sound_in_background(f"./resources/{random_file}")

    def add_event(self, event):
        global events
        timestamp = self.get_timestamp()
        events.append((timestamp, event))
        if (len(events) > EVENTS_SIZE):
            events = events[1:]


    def get_event_duration(self, event):
        flag=True
        events_list = reversed(events)
        for ev in events_list:
            if ev[1] == event and flag:
                stop_time = ev[0]
                start_time = ev[0]
                flag=False
            elif ev[1] == event and not flag:
                start_time = ev[0]
            elif ev[1] != event:
                return (stop_time - start_time)
        return 

    def find_event_duration(self, target_event):
        """
        Finds the duration of a given event in a list of (timestamp, event) tuples.
        
        Args:
            events (list of tuples): List of (timestamp, event) tuples sorted by timestamp.
            target_event (str): The event for which the duration is to be calculated.
        
        Returns:
            int or float: The duration of the event in the same units as the timestamps, or 0 if not found.
        """
        # Filter timestamps for the target event
        timestamps = [timestamp for timestamp, event in events if event == target_event]
        
        # If no timestamps are found, return 0
        if not timestamps:
            return 0
        
        # Calculate the duration
        duration = max(timestamps) - min(timestamps)
        return duration

    def left_or_right(self, dog_bbox):
        # Compute x_max and y_max for the dog's bounding box
        try:
            dog_x_min = dog_bbox.xmin()
            dog_y_min = dog_bbox.ymin()
            dog_height = dog_bbox.height()
            dog_width = dog_bbox.width()
        except:
            return
        dog_x_middle  = dog_x_min + (dog_width/2)
        local_sign = (dog_x_middle - 0.5)*-1 
        local_sign = local_sign/abs(local_sign)
        global angle
        print ("Centering dog")
        step = local_sign * 1
        angle += step
        if  angle>= 150 or angle <=30:
            return
        print(angle)
        if not app.options_menu.no_arm_control:
            arm_control.set_arm_horizontal_angle(angle)
        return 

    def is_pet_centered(self, dog_bbox):
        # Compute x_max and y_max for the dog's bounding box
        dog_x_min = dog_bbox.xmin()
        dog_y_min = dog_bbox.ymin()
        dog_height = dog_bbox.height()
        dog_width = dog_bbox.width()
        dog_x_middle  = dog_x_min + (dog_width/2)
        threshold = 0.1
        return  0.3 < dog_x_middle < 0.7

    def is_pet_on_couch(self, dog_bbox, couch_bbox):
        """
        Determines if the dog's bounding box is fully contained within any of the couch bounding boxes.

        Args:
            dog_bbox (object): Bounding box of the dog with methods xmin(), ymin(), height(), and width().
            couch_bbox (list): List of bounding box objects of couches, each with methods xmin(), ymin(), height(), and width().

        Returns:
            bool: True if the dog's bounding box is fully contained within any couch's bounding box, False otherwise.
        """
        # Compute x_max and y_max for the dog's bounding box
        dog_x_min = dog_bbox.xmin()
        dog_y_min = dog_bbox.ymin()
        dog_height = dog_bbox.height()
        dog_width = dog_bbox.width()
        dog_x_max = dog_x_min + dog_width
        dog_y_max = dog_y_min + dog_height

        # Check against each couch bounding box
        for couch in couch_bbox:
            couch_x_min = couch.xmin()
            couch_y_min = couch.ymin()
            couch_height = couch.height()
            couch_width = couch.width()
            couch_x_max = couch_x_min + couch_width
            couch_y_max = couch_y_min + couch_height

            # Check if the dog's bounding box is fully contained within the current couch bounding box
            is_fully_within_x = dog_x_min >= couch_x_min and dog_x_max <= couch_x_max
            is_fully_within_y = dog_y_min >= couch_y_min and dog_y_max <= couch_y_max

            if is_fully_within_x and is_fully_within_y:
                return True

        return False

    def get_current_event(self):
        event_names = [event for _, event in events]
        event_counter = Counter(event_names)
        event_to_reduce = Pet_State.PET_HOMING
        new_count = event_counter[event_to_reduce] // 3
        # Create a new list with the reduced occurrences
        reduced_events = []
        for event in events:
            if event == event_to_reduce and event_counter[event_to_reduce] > new_count:
                event_counter[event_to_reduce] -= 1  # Skip occurrences to reduce count
            else:
                reduced_events.append(event)
        most_common_event, occurrences = event_counter.most_common(1)[0]

        return most_common_event

def get_parser():
    parser = get_default_parser()
    parser.add_argument("--no-arm-control", action="store_true", help="Run the app without arm control")
    return parser

# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    global cur_event
    global cooldown_period
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK

    # Using the user_data to count the number of frames
    user_data.increment()
    string_to_print = ""
    
    if (user_data.get_count() == 1):    
        string_to_print = """

      T A I L O 
           __
      (___()'`;
      /,    /`
      \\"--\\
    
    """

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
    detection_count = 0
    pet_found = False
    chair_or_couch_bbox_list = []
    # print (detection.values())
    for detection in detections:
        if detection.get_label() in ["chair", "couch"]:
            chair_or_couch_bbox_list.append(detection.get_bbox())
    detection_map = {det.get_label(): det.get_bbox() for det in detections}
    dog_bbox = (detection_map.get("dog", None))

    if dog_bbox is None:
        user_data.add_event(Pet_State.PET_HOMING)
    else:
        if not user_data.is_pet_centered(dog_bbox):
            user_data.add_event(Pet_State.PET_NOT_CENTERED)
        else:
            if len(chair_or_couch_bbox_list) == 0:
                user_data.add_event (Pet_State.PET_LOCKED)
            else:
                if user_data.is_pet_on_couch(dog_bbox, chair_or_couch_bbox_list):
                    user_data.add_event(Pet_State.PET_ON_COUCH)
                #else if... (dog at the door? dog barking?)
                else:
                    user_data.add_event(Pet_State.PET_LOCKED)
    if cur_event is None:
        cur_event = Pet_State.PET_IDLE
        
    if cooldown_period < 1:
        prev_event = cur_event
        cur_event = user_data.get_current_event()
        print (f'{prev_event} --> {cur_event}')
        match(cur_event):
            case Pet_State.PET_HOMING:
                if prev_event == Pet_State.PET_ON_COUCH:
                    user_data.treat_pet()
                user_data.scan_pet()
                cooldown_period = 3

            case Pet_State.PET_NOT_CENTERED:
                print("track_pet")
                user_data.left_or_right(dog_bbox)
                cooldown_period = 3
                
            case Pet_State.PET_ON_COUCH:
                duration = user_data.find_event_duration(Pet_State.PET_ON_COUCH)
                if WARN_DURATION < duration < SHOOT_DURATION:
                    user_data.warn_pet()
                    cooldown_period = 5 * SEC
                elif duration >= SHOOT_DURATION:
                    punish_pet()
                    cooldown_period = 3 * SEC
                else: #less than warn duration, grace
                    cooldown_period = 1 * SEC
                    
            case Pet_State.PET_LOCKED:
                if prev_event == Pet_State.PET_ON_COUCH:
                    treat_pet()

    cooldown_period -= 1

    if string_to_print != "":
        print(string_to_print)

    return Gst.PadProbeReturn.OK


if __name__ == "__main__":
    parser = get_parser()
    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    treat_control.init_treat_control()
    app = GStreamerDetectionApp(app_callback, user_data, parser)
    if not app.options_menu.no_arm_control:
        try:
                arm_control.enable_arm()
                arm_control.set_arm_horizontal_angle(90)
        except :
            print("Error - arm control doesn't work")
            print("Use --no-arm-control")
            
            os._exit(1)
    app.run()


# Pseudo Code:

# # Start Homing
# if dog not in frame:
#     add_event(pet_homing)    
# else #dog in frame:
#     if dog not in middle of frame:
#         add_event(pet_not_centered)        
#     else # Locked                
#         if dog on couch:
#             add_event(pet_on_couch)
#         else if .... (near the door? barking?)
#         else 
#             add_event(pet_locked)
            
# prev_event = cur_event
# cur_event = max(events) #most common event

# cooldown_period = 30
# if not cooldown_period:
#     switch (cur_event)
#         missing_dog: scan_dog, cooldown_period = 30
#         dog_not_centered: move arm, cooldown_period = 50
#         dog_on_couch: 
#             if dog_on_couch_cnt > 100: warn_dog, cooldown_period = 200
#             if dog_on_couch_cnt > 500: shoot_dog, cooldown_period = 200
#         dog_in_frame:
#             if prev_event is dog_on_couch give treat
