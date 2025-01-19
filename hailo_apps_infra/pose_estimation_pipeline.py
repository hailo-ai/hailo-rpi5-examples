import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import argparse
import multiprocessing
import numpy as np
import setproctitle
import cv2
import time
import hailo
from hailo_apps_infra.hailo_rpi_common import (
    get_default_parser,
    detect_hailo_arch,
)
from hailo_apps_infra.gstreamer_helper_pipelines import(
    QUEUE,
    SOURCE_PIPELINE,
    INFERENCE_PIPELINE,
    INFERENCE_PIPELINE_WRAPPER,
    TRACKER_PIPELINE,
    USER_CALLBACK_PIPELINE,
    DISPLAY_PIPELINE,
)
from hailo_apps_infra.gstreamer_app import (
    GStreamerApp,
    app_callback_class,
    dummy_callback
)

#-----------------------------------------------------------------------------------------------
# User Gstreamer Application
# -----------------------------------------------------------------------------------------------

# This class inherits from the hailo_rpi_common.GStreamerApp class

class GStreamerPoseEstimationApp(GStreamerApp):
    def __init__(self, app_callback, user_data):
        parser = get_default_parser()
        args = parser.parse_args()
        # Call the parent class constructor
        super().__init__(args, user_data)
        # Additional initialization code can be added here
        # Set Hailo parameters these parameters should be set based on the model used
        self.batch_size = 2
        self.video_width = 1280
        self.video_height = 720


        # Determine the architecture if not specified
        if args.arch is None:
            detected_arch = detect_hailo_arch()
            if detected_arch is None:
                raise ValueError("Could not auto-detect Hailo architecture. Please specify --arch manually.")
            self.arch = detected_arch
            print(f"Auto-detected Hailo architecture: {self.arch}")
        else:
            self.arch = args.arch



        # Set the HEF file path based on the architecture
        if args.hef_path:
            self.hef_path = args.hef_path
        elif self.arch == "hailo8":
            self.hef_path = os.path.join(self.current_path, '../resources/yolov8m_pose.hef')
        else:  # hailo8l
            self.hef_path = os.path.join(self.current_path, '../resources/yolov8s_pose_h8l.hef')

        self.app_callback = app_callback

        # Set the post-processing shared object file
        self.post_process_so = os.path.join(self.current_path, '../resources/libyolov8pose_postprocess.so')
        self.post_process_function = "filter_letterbox"


        # Set the process title
        setproctitle.setproctitle("Hailo Pose Estimation App")

        self.create_pipeline()

    def get_pipeline_string(self):
        source_pipeline = SOURCE_PIPELINE(video_source=self.video_source, video_width=self.video_width, video_height=self.video_height)
        infer_pipeline = INFERENCE_PIPELINE(
            hef_path=self.hef_path,
            post_process_so=self.post_process_so,
            post_function_name=self.post_process_function,
            batch_size=self.batch_size
        )
        infer_pipeline_wrapper = INFERENCE_PIPELINE_WRAPPER(infer_pipeline)
        tracker_pipeline = TRACKER_PIPELINE(class_id=0)
        user_callback_pipeline = USER_CALLBACK_PIPELINE()

        display_pipeline = DISPLAY_PIPELINE(video_sink=self.video_sink, sync=self.sync, show_fps=self.show_fps)
        pipeline_string = (
            f'{source_pipeline} !'
            f'{infer_pipeline_wrapper} ! '
            f'{tracker_pipeline} ! '
            f'{user_callback_pipeline} ! '
            f'{display_pipeline}'
        )
        print(pipeline_string)
        return pipeline_string

if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = app_callback_class()
    app = GStreamerPoseEstimationApp(dummy_callback, user_data)
    app.run()
