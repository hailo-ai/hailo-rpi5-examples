import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np
import hailo
import multiprocessing as mp
import queue
import time

from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
from hailo_apps.hailo_app_python.core.common.core import get_default_parser
from hailo_apps.hailo_app_python.apps.pose_estimation.pose_estimation_pipeline import GStreamerPoseEstimationApp

from community_projects.fruit_ninja.pygame_fruit_ninja import PygameFruitNinja

CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for wrist keypoints

"""
Fruit Ninja main application.

This module integrates Hailo's pose estimation pipeline with a Pygame-based Fruit Ninja game.
It manages inter-process communication between the pose estimation process and the game process,
extracts hand positions from pose estimation, and injects fruit detections into the video stream.
"""

class user_app_callback_class(app_callback_class):
    """
    User callback class for fruit ninja game integration.

    Manages communication between pose estimation pipeline and pygame game.
    """

    def __init__(self, parser: any) -> None:
        super().__init__()

        # Parse command line arguments
        args = parser.parse_args()
        self.frame_width = args.video_width if hasattr(args, 'video_width') else 1280
        self.frame_height = args.video_height if hasattr(args, 'video_height') else 720

        # Create queues for inter-process communication
        self.hand_positions_queue = mp.Queue(maxsize=10)
        self.fruits_queue = mp.Queue(maxsize=100)

        # Start pygame process
        self.pygame_process = mp.Process(
            target=PygameFruitNinja.run_game,
            args=(self.hand_positions_queue, self.fruits_queue, self.frame_width, self.frame_height)
        )
        self.pygame_process.start()

        print(f"Fruit Ninja game initialized with frame size: {self.frame_width}x{self.frame_height}")

    def __del__(self) -> None:
        """Clean up pygame process on destruction."""
        if hasattr(self, 'pygame_process') and self.pygame_process.is_alive():
            self.pygame_process.terminate()
            self.pygame_process.join(timeout=2)
            if self.pygame_process.is_alive():
                self.pygame_process.kill()


def app_callback(pad: any, info: any, user_data: 'user_app_callback_class') -> Gst.PadProbeReturn:
    """
    Main callback function for processing pose estimation data.

    Args:
        pad (any): GStreamer pad
        info (any): Probe info containing buffer data
        user_data (user_app_callback_class): User callback class instance

    Returns:
        Gst.PadProbeReturn: Continue processing
    """
    user_data.increment()

    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Extract hand positions from pose estimation
    hand_positions = {}
    for detection in detections:
        if detection.get_label() != "person":
            continue

        # Get tracking ID for this person
        track_objects = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if not track_objects:
            continue
        track_id = track_objects[0].get_id()

        # Get pose landmarks
        landmark_objects = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
        if not landmark_objects:
            continue
        landmarks = landmark_objects[0].get_points()

        # Get bbox for this detection
        bbox = detection.get_bbox()
        # bbox.xmin(), bbox.ymin(), bbox.width(), bbox.height() are normalized (0-1)

        # Extract wrist positions (left_wrist: index 9, right_wrist: index 10)
        for i, wrist in enumerate(['left_wrist', 'right_wrist']):
            keypoint_index = {'left_wrist': 9, 'right_wrist': 10}[wrist]
            if keypoint_index < len(landmarks):
                point = landmarks[keypoint_index]
                # Reason: Only use keypoints with sufficient confidence
                if hasattr(point, 'confidence') and callable(point.confidence):
                    if point.confidence() < CONFIDENCE_THRESHOLD:
                        continue
                # Convert from bbox-relative to global frame coordinates
                x = int((point.x() * bbox.width() + bbox.xmin()) * user_data.frame_width)
                y = int((point.y() * bbox.height() + bbox.ymin()) * user_data.frame_height)
                # Create unique ID for each hand: (track_id << 1) + hand_index
                hand_id = (track_id << 1) + i
                hand_positions[hand_id] = (x, y)

    # Send hand positions to pygame (non-blocking)
    try:
        if hand_positions:
            user_data.hand_positions_queue.put_nowait(hand_positions)
    except queue.Full:
        pass  # Skip if queue is full

    # Get fruit positions from pygame and add them as detections
    fruits_to_add = []
    try:
        while True:
            fruit_data = user_data.fruits_queue.get_nowait()
            fruits_to_add.append(fruit_data)
    except queue.Empty:
        pass

    # Add fruits as hailo detections to the ROI
    for fruit_data in fruits_to_add:
        fruit_type = fruit_data['type']
        x, y = fruit_data['position']
        size = fruit_data['size']
        class_id = fruit_data['class_id']

        # Convert pygame coordinates to normalized coordinates
        norm_x = x / user_data.frame_width
        norm_y = y / user_data.frame_height
        norm_size_x = size / user_data.frame_width
        norm_size_y = size / user_data.frame_height

        # Create hailo bounding box (left, top, width, height in normalized coordinates)
        bbox = hailo.HailoBBox(
            max(0.0, norm_x - norm_size_x/2),  # left
            max(0.0, norm_y - norm_size_y/2),  # top
            min(1.0, norm_size_x),             # width
            min(1.0, norm_size_y)              # height
        )

        # Create hailo detection object
        detection = hailo.HailoDetection(
            bbox=bbox,
            label=fruit_type,
            index=class_id,
            confidence=1.0
        )

        # Add detection to ROI
        roi.add_object(detection)

    return Gst.PadProbeReturn.OK


if __name__ == "__main__":
    # Create parser with default options
    parser = get_default_parser()

    # Set default frame rate for better performance
    parser.set_defaults(frame_rate=30)

    # Create user data instance
    user_data = user_app_callback_class(parser)

    # Create and run the pose estimation app
    app = GStreamerPoseEstimationApp(app_callback, user_data, parser)
    try:
        print("Starting Fruit Ninja game...")
        app.run()
    except KeyboardInterrupt:
        print("\nShutting down Fruit Ninja game...")
    finally:
        # Clean up
        if hasattr(user_data, 'pygame_process') and user_data.pygame_process.is_alive():
            user_data.pygame_process.terminate()
            user_data.pygame_process.join(timeout=2)
            if user_data.pygame_process.is_alive():
                user_data.pygame_process.kill()