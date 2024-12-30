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
from hailo_rpi_common import (
    get_default_parser,
    QUEUE,
    SOURCE_PIPELINE,
    INFERENCE_PIPELINE,
    USER_CALLBACK_PIPELINE,
    GStreamerApp,
    app_callback_class,
    dummy_callback,
    detect_hailo_arch,
)

class GStreamerInstanceSegmentationApp(GStreamerApp):
    def __init__(self, app_callback, user_data):
        parser = get_default_parser()
        args = parser.parse_args()
        # Appel au constructeur parent
        super().__init__(args, user_data)

        self.batch_size = 2
        self.network_width = 640
        self.network_height = 640
        self.network_format = "RGB"

        if args.arch is None:
            detected_arch = detect_hailo_arch()
            if detected_arch is None:
                raise ValueError("Could not auto-detect Hailo architecture. Please specify --arch manually.")
            self.arch = detected_arch
            print(f"Auto-detected Hailo architecture: {self.arch}")
        else:
            self.arch = args.arch

        if args.hef_path:
            self.hef_path = args.hef_path
        elif self.arch == "hailo8":
            self.hef_path = os.path.join(self.current_path, '../resources/yolov5m_seg.hef')
        elif 'yolov8n_seg' in self.hef_path:
            self.hef_path = os.path.join(self.current_path, '../resources/yolov8n_seg.hef')
        else:  # hailo8l
            self.hef_path = os.path.join(self.current_path, '../resources/yolov5n_seg_h8l_mz.hef')

        if 'yolov5m_seg' in self.hef_path:
            self.config_file = os.path.join(self.current_path, '../resources/yolov5m_seg.json')
        elif 'yolov5n_seg' in self.hef_path:
            self.config_file = os.path.join(self.current_path, '../resources/yolov5n_seg.json')
        elif 'yolov8n_seg' in self.hef_path:
            self.config_file = os.path.join(self.current_path, '../resources/yolov8n_seg.json')
        else:
            raise ValueError("HEF version not supported, please provide a config file")

        self.default_post_process_so = os.path.join(self.current_path, '../resources/libyolov5seg_postprocess.so')
        self.post_function_name = "yolov5seg"
        self.app_callback = app_callback

        self.create_pipeline()

    def get_pipeline_string(self):
        # Pipeline source et inference identique
        source_pipeline = SOURCE_PIPELINE(video_source=self.video_source)
        infer_pipeline = INFERENCE_PIPELINE(
            hef_path=self.hef_path,
            post_process_so=self.default_post_process_so,
            post_function_name=self.post_function_name,
            batch_size=self.batch_size,
            config_json=self.config_file,
        )
        user_callback_pipeline = USER_CALLBACK_PIPELINE()

        # On insÃ¨re videoconvert avant cairooverlay pour assurer un format compatible
        # On garde fpsdisplaysink pour l'affichage final
        pipeline_string = (
            f'{source_pipeline} '
            f'{infer_pipeline} ! '
            f'{user_callback_pipeline} ! '
            # hailooverlay
            f'{QUEUE("hailo_display_hailooverlay_q")} ! '
            f'hailooverlay name=hailo_overlay ! '
            # videoconvert pour assurer format compatible cairooverlay
            f'{QUEUE("pre_cairo_convert_q")} ! '
            f'videoconvert name=pre_cairo_convert ! '
            # cairooverlay
            f'{QUEUE("cairo_q")} ! '
            f'cairooverlay name=cairo_overlay ! '
            # videoconvert aprÃ¨s cairooverlay
            f'{QUEUE("hailo_display_videoconvert_q")} ! '
            f'videoconvert name=hailo_display_videoconvert n-threads=2 qos=false ! '
            # Ajout du tee
            f'tee name=t '
            # Branche pour l'affichage local
            f't. ! queue ! '
            f'fpsdisplaysink name=hailo_display video-sink={self.video_sink} sync={self.sync} text-overlay={self.show_fps} signal-fps-measurements=true '
            # Branche pour le streaming RTMP
            f't. ! queue ! '
            f'x264enc tune=zerolatency bitrate=1200 speed-preset=superfast ! '
            f'flvmux streamable=true ! '
            f'rtmpsink location="rtmp://localhost/live/stream live=1" '
            # # fpsdisplaysink pour l'affichage final
            # f'{QUEUE("hailo_display_q")} ! '
            # f'fpsdisplaysink name=hailo_display video-sink={self.video_sink} sync={self.sync} text-overlay={self.show_fps} signal-fps-measurements=true '
        )
        print(pipeline_string)
        return pipeline_string
