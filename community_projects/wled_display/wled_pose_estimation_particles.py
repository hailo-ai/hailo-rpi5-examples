import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np
import hailo

from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.hailo_app_python.apps.pose_estimation.pose_estimation_pipeline import GStreamerPoseEstimationApp
from hailo_apps.hailo_app_python.core.common.core import get_default_parser

from wled_display import WLEDDisplay, add_parser_args
from particle_simulation import ParticleSimulation

class user_app_callback_class(app_callback_class):
    def __init__(self, parser):
        super().__init__()

        self.wled = WLEDDisplay(parser=parser)
        if self.wled.wled_enabled:
            particle_size=1
        else:
            particle_size=10

        self.particle_simulation = ParticleSimulation(screen_height=self.wled.height,
                                                      screen_width=self.wled.width,
                                                      particle_size=particle_size)

    def __del__(self):
        self.particle_simulation = None


def app_callback(pad, info, user_data):
    user_data.increment()

    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    hand_positions = {}
    for detection in detections:
        if detection.get_label() != "person":
            continue
        track_id = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id()
        landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)[0].get_points()
        for i, wrist in enumerate(['left_wrist', 'right_wrist']):
            keypoint_index = {'left_wrist': 9, 'right_wrist': 10}[wrist]
            point = landmarks[keypoint_index]
            x = int(point.x() * user_data.wled.width)
            y = int(point.y() * user_data.wled.height)
            hand_positions[(track_id << 1) + i] = (x, y)

    user_data.particle_simulation.update_player_positions(hand_positions)
    user_data.particle_simulation.update()

    frame = user_data.particle_simulation.get_frame(
        user_data.wled.width, user_data.wled.height
    )
    user_data.wled.frame_queue.put(frame)

    return Gst.PadProbeReturn.OK


if __name__ == "__main__":
    # Create a modified parser to include WLED display options
    parser = get_default_parser()
    # Drawing every frame on the Pi is too slow, so we update the frame rate to 15
    # You can modify this from the command line with the --frame-rate flag
    parser.set_defaults(
        frame_rate=15,          # Override default frame rate
    )
    # Add WLED display options
    add_parser_args(parser)
    # Create an instance of the user app callback class
    user_data = user_app_callback_class(parser)
    app = GStreamerPoseEstimationApp(app_callback, user_data, parser)
    app.run()