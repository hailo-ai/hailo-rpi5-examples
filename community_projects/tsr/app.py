from hailo_apps_infra.hailo_rpi_common import app_callback_class
from gps_calculations import gps_task, latest_gps_data
from get_usb_gps import get_usb_gps_devices
from pipeline import GStreamerTsrApp
from gi.repository import Gst
import threading
import asyncio
import pathlib
import hailo
import csv
import gi
import os

# User-defined class to be used in the callback function: Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.save_csv_path = os.path.join(pathlib.Path(__file__).parent.resolve(), 'tsr_mapping.csv')
        print(self.save_csv_path)
        with open(self.save_csv_path, 'a', newline='') as fd:
            writer = csv.writer(fd)
            writer.writerow(['id', 'latitude', 'longitude', 'altitude'])


    def start_gps_task(self):
        def run_gps_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(gps_task(get_usb_gps_devices()))

        gps_thread = threading.Thread(target=run_gps_task)
        gps_thread.daemon = True
        gps_thread.start()

# User-defined callback function: This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()  # Get the GstBuffer from the probe info
    if buffer is None:  # Check if the buffer is valid
        return Gst.PadProbeReturn.OK
    
    user_data.increment()  # using the user_data to count the number of frames for debugging purposes

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Parse the detections
    for detection in detections:
        class_id = detection.get_class_id()
        track_id = 0
        track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if len(track) > 0:
            track_id = track[0].get_id()
        if class_id == 12:  # COCO 1 based, 12 - stop sign
            with open(user_data.save_csv_path, 'a', newline='') as fd:
                writer = csv.writer(fd)
                writer.writerow([track_id, latest_gps_data['latitude'], latest_gps_data['longitude'], latest_gps_data['altitude']])

    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    gi.require_version('Gst', '1.0')
    user_data = user_app_callback_class()
    app = GStreamerTsrApp(app_callback, user_data)
    app.run()
