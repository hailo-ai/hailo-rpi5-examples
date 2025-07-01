import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import numpy as np
import pathlib
import hailo
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from pipeline import GStreamerDetectionCropperApp

# User-defined class to be used in the callback function: Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):

    def calculate_average_depth(self, depth_mat):
        depth_values = np.array(depth_mat).flatten()  # Flatten the array and filter out outlier pixels
        try:
            m_depth_values = depth_values[depth_values <= np.percentile(depth_values, 95)]  # drop 5% of highest values (outliers)          
        except Exception as e:
            m_depth_values = np.array([])
        if len(m_depth_values) > 0:
            average_depth = np.mean(m_depth_values)  # Calculate the average depth of the pixels
        else:
            average_depth = 0  # Default value if no valid pixels are found
        return average_depth

# User-defined callback function: This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()  # Get the GstBuffer from the probe info
    if buffer is None:  # Check if the buffer is valid
        return Gst.PadProbeReturn.OK
    
    user_data.increment()  # Using the user_data to count the number of frames

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    # Parse the detections
    for detection in detections:
        track_id = 0
        track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if len(track) > 0:
            track_id = track[0].get_id()
        depth_mat = detection.get_objects_typed(hailo.HAILO_DEPTH_MASK)
        if len(depth_mat) > 0:  # since depth is only on detections
            detection_average_depth = user_data.calculate_average_depth(depth_mat[0].get_data())
        else:
            detection_average_depth = 0
        print(f'Frame {user_data.frame_count}, Detection {detection.get_label()} ({track_id}) average depth: {detection_average_depth:.2f}')

    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    user_data = user_app_callback_class()
    app = GStreamerDetectionCropperApp(app_callback, user_data, pathlib.Path(__file__).parent.resolve())
    app.run()
