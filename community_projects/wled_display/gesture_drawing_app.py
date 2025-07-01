"""
gesture_drawing_app.py

By default, we assume a single WLED panel of size 20×20 (panels=1).
If you have multiple panels, set panels accordingly.

We now refer to the 'chest' region instead of 'belly button';
the logic is identical: left wrist must be inside a shrunk bounding box
(shoulders & hips) to enable drawing.
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import hailo

from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.hailo_app_python.apps.pose_estimation.pose_estimation_pipeline import GStreamerPoseEstimationApp
from hailo_apps.hailo_app_python.core.common.core import get_default_parser

from wled_display import WLEDDisplay, add_parser_args
from drawing_board import DrawingBoard

# Typical body indices in your pose model (COCO-like)
LEFT_WRIST_IDX = 9
RIGHT_WRIST_IDX = 10
LEFT_SHOULDER_IDX = 5
RIGHT_SHOULDER_IDX = 6
LEFT_HIP_IDX = 11
RIGHT_HIP_IDX = 12


class GestureDrawingCallback(app_callback_class):
    def __init__(self, parser):

        """
        :param mirror_hands:  If True, swap 'left' <-> 'right'
        """
        super().__init__()
        self.mirror_hands = True # mirror left and right landmarks

        # Create the WLED display
        self.wled = WLEDDisplay(parser=parser)

        # Process every frame
        self.frame_skip = 1

        # The DrawingBoard: handles chest-enabling, color picking, T-pose, etc.
        self.drawing_board = DrawingBoard(
            width=self.wled.width,
            height=self.wled.height,
        )

    def __del__(self):
        self.drawing_board = None


def app_callback(pad, info, user_data):
    """
    GStreamer pad-probe callback:
      - For each detected 'person', retrieve bounding box + landmarks
      - Convert them into the global coords
      - Forward them to the DrawingBoard.
    """
    user_data.increment()
    if user_data.get_count() % user_data.frame_skip != 0:
        return Gst.PadProbeReturn.OK

    buffer = info.get_buffer()
    if not buffer:
        return Gst.PadProbeReturn.OK

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    for detection in detections:
        if detection.get_label() != "person":
            continue

        # Track ID (for multi-person)
        track_id_obj = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        track_id = track_id_obj[0].get_id() if track_id_obj else 0

        # The detection bounding box in [0..1]
        bbox = detection.get_bbox()

        # Landmarks in [0..1] relative to the detection box
        landmarks_obj = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
        if not landmarks_obj:
            continue
        points = landmarks_obj[0].get_points()

        # Swap left<->right if mirror_hands=True
        if user_data.mirror_hands:
            lw_idx = RIGHT_WRIST_IDX
            rw_idx = LEFT_WRIST_IDX
            ls_idx = RIGHT_SHOULDER_IDX
            rs_idx = LEFT_SHOULDER_IDX
            lh_idx = RIGHT_HIP_IDX
            rh_idx = LEFT_HIP_IDX
        else:
            lw_idx = LEFT_WRIST_IDX
            rw_idx = RIGHT_WRIST_IDX
            ls_idx = LEFT_SHOULDER_IDX
            rs_idx = RIGHT_SHOULDER_IDX
            lh_idx = LEFT_HIP_IDX
            rh_idx = RIGHT_HIP_IDX

        # Convert detection-local coords [0..1] to total LED coords
        def to_panel_coords(pt):
            # check pt confidence
            if pt.confidence() < 0.5:
                return None
            x_glob = (pt.x() * bbox.width() + bbox.xmin()) * user_data.drawing_board.width
            y_glob = (pt.y() * bbox.height() + bbox.ymin()) * user_data.drawing_board.height
            return int(x_glob), int(y_glob)

        # Extract final pixel coords
        left_wrist_px     = to_panel_coords(points[lw_idx])
        right_wrist_px    = to_panel_coords(points[rw_idx])
        left_shoulder_px  = to_panel_coords(points[ls_idx])
        right_shoulder_px = to_panel_coords(points[rs_idx])
        left_hip_px       = to_panel_coords(points[lh_idx])
        right_hip_px      = to_panel_coords(points[rh_idx])

        # Update the DrawingBoard with these pixel coords
        user_data.drawing_board.update_player_pose(
            track_id=track_id,
            left_wrist=left_wrist_px,
            right_wrist=right_wrist_px,
            left_shoulder=left_shoulder_px,
            right_shoulder=right_shoulder_px,
            left_hip=left_hip_px,
            right_hip=right_hip_px
        )

    # Once all detections processed, update + get final frame
    user_data.drawing_board.update()
    final_frame = user_data.drawing_board.get_frame()
    user_data.wled.frame_queue.put(final_frame)

    return Gst.PadProbeReturn.OK


if __name__ == "__main__":
    """
    Example usage:
      For a single 20x20 panel (default), run:
        python gesture_drawing_app.py
      If you have multiple panels, e.g. 2 horizontally, run:
        python gesture_drawing_app.py (with panels=2)
    """
    # Create a modified parser to include WLED display options
    parser = get_default_parser()
    # Add WLED display options
    add_parser_args(parser)
    # Create an instance of the user app callback class
    user_data = GestureDrawingCallback(parser)
    app = GStreamerPoseEstimationApp(app_callback, user_data, parser)
    app.run()
