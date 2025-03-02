from hailo_apps_infra.gstreamer_helper_pipelines import DISPLAY_PIPELINE, INFERENCE_PIPELINE, INFERENCE_PIPELINE_WRAPPER, OVERLAY_PIPELINE, SOURCE_PIPELINE, TRACKER_PIPELINE, USER_CALLBACK_PIPELINE
from hailo_apps_infra.hailo_rpi_common import detect_hailo_arch, get_default_parser
from hailo_apps_infra.gstreamer_app import GStreamerApp
import setproctitle
import os
import gi

# User Gstreamer Application: This class inherits from the hailo_rpi_common.GStreamerApp class
class GStreamerTsrApp(GStreamerApp):
    def __init__(self, app_callback, user_data):
        gi.require_version('Gst', '1.0')
        parser = get_default_parser()
        args = parser.parse_args()

        # Determine the architecture if not specified
        if args.arch is None:
            detected_arch = detect_hailo_arch()
            if detected_arch is None:
                raise ValueError('Could not auto-detect Hailo architecture. Please specify --arch manually.')
            self.arch = detected_arch
        else:
            self.arch = args.arch
            
        super().__init__(args, user_data)  # Call the parent class constructor
        self.app_callback = app_callback
        setproctitle.setproctitle("Hailo TSR App")  # Set the process title

        # Set Hailo parameters (for detection neural network), these parameters should be set based on the model used
        self.batch_size = 2
        self.thresholds_str = (
            f"nms-score-threshold=0.3 "
            f"nms-iou-threshold=0.45 "
            f"output-format-type=HAILO_FORMAT_TYPE_FLOAT32"
        )

        # Set the detection HEF file path based on the arch
        if self.arch == "hailo8":
            self.detection_hef_path = os.path.join(self.current_path, '../resources/yolov8m.hef')
        else:  # hailo8l
            self.detection_hef_path = os.path.join(self.current_path, '../resources/yolov8s_h8l.hef')

        # Set the post-processing shared object file
        self.detection_post_process_so = os.path.join(self.current_path, '../resources/libyolo_hailortpp_postprocess.so')
        self.detection_post_function_name = "filter_letterbox"
            
        user_data.start_gps_task()  # start in the background the GPS
        self.create_pipeline()

    def get_pipeline_string(self):
        source_pipeline = SOURCE_PIPELINE(self.video_source, self.video_width, self.video_height)
        detection_pipeline = INFERENCE_PIPELINE(
            hef_path=self.detection_hef_path,
            post_process_so=self.detection_post_process_so,
            post_function_name=self.detection_post_function_name,
            batch_size=self.batch_size,
            additional_params=self.thresholds_str,
            name='detection_inference')
        detection_pipeline_wrapper = INFERENCE_PIPELINE_WRAPPER(detection_pipeline, name='inference_wrapper_detection')
        tracker_pipeline = TRACKER_PIPELINE(class_id=12)  # for what COCO class id (1 based) across frames will be tracked (12=stop sign)
        user_callback_pipeline = USER_CALLBACK_PIPELINE()
        display_pipeline = DISPLAY_PIPELINE(video_sink=self.video_sink, sync=self.sync, show_fps=self.show_fps)

        return (
            f'{source_pipeline} ! '
            f'{detection_pipeline_wrapper} ! '
            f'{tracker_pipeline} ! '
            f'{user_callback_pipeline} ! '
            f'{display_pipeline}'
        )
