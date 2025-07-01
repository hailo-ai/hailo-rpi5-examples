import gi
gi.require_version('Gst', '1.0')
import os
import setproctitle
from hailo_apps.hailo_app_python.core.common.core import get_default_parser
from hailo_apps.hailo_app_python.core.common.installation_utils import detect_hailo_arch
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_helper_pipelines import CROPPER_PIPELINE, DISPLAY_PIPELINE, INFERENCE_PIPELINE, INFERENCE_PIPELINE_WRAPPER, SOURCE_PIPELINE, TRACKER_PIPELINE, USER_CALLBACK_PIPELINE
from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import GStreamerApp

# User Gstreamer Application: This class inherits from the hailo_rpi_common.GStreamerApp class
class GStreamerDetectionCropperApp(GStreamerApp):
    def __init__(self, app_callback, user_data, app_path, parser=None):
        if parser == None:
            parser = get_default_parser()
        parser.add_argument('--apps_infra_path', default='None', help='Required argument. Path to the hailo-apps-infra folder.')
        super().__init__(parser, user_data)  # Call the parent class constructor
        # Determine the architecture if not specified
        if self.options_menu.arch is None:
            detected_arch = detect_hailo_arch()
            if detected_arch is None:
                raise ValueError('Could not auto-detect Hailo architecture. Please specify --arch manually.')
            self.arch = detected_arch
        else:
            self.arch = self.options_menu.arch
            print(f'Using Hailo architecture: {self.arch}')

        if self.options_menu.apps_infra_path is None:
            raise ValueError('Please specify path to the hailo-apps-infra folder')
        elif not os.path.exists(self.options_menu.apps_infra_path):
            raise ValueError('Please specify valid path to the hailo-apps-infra folder')

        
        self.app_callback = app_callback
        setproctitle.setproctitle("Hailo Detection Cropper App")  # Set the process title

        # Set Hailo parameters (for detection neural network) these parameters should be set based on the model used
        self.batch_size = 2
        self.thresholds_str = (
            f"nms-score-threshold=0.3 "
            f"nms-iou-threshold=0.45 "
            f"output-format-type=HAILO_FORMAT_TYPE_FLOAT32"
        )

        # Set the HEF file path & depth post processing method name based on the arch
        if self.arch == "hailo8":
            self.detection_hef_path = self.options_menu.apps_infra_path + '/resources/yolov8m.hef'
            self.depth_hef_path = self.options_menu.apps_infra_path + '/resources/scdepthv3.hef'
        else:  # hailo8l
            self.detection_hef_path = self.options_menu.apps_infra_path + '/resources/yolov8s_h8l.hef'
            self.depth_hef_path = self.options_menu.apps_infra_path + '/resources/scdepthv3_h8l.hef'
        self.depth_post_function_name = "filter_scdepth"

        # Set the post-processing shared object file
        self.detection_post_process_so = self.options_menu.apps_infra_path + '/resources/libyolo_hailortpp_postprocess.so'
        self.detection_post_function_name = "filter_letterbox"
        self.depth_post_process_so = self.options_menu.apps_infra_path + '/resources/libdepth_postprocess.so'
        self.post_process_so_cropper = os.path.join(app_path, 'resources/libdetections_cropper.so')
        self.cropper_post_function_name = "crop_detections"

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
        tracker_pipeline = TRACKER_PIPELINE(class_id=1)  # for what COCO class id (1 based) across frames will be tracked (1=person)
        depth_pipeline = INFERENCE_PIPELINE(
            hef_path=self.depth_hef_path,
            post_process_so=self.depth_post_process_so,
            post_function_name=self.depth_post_function_name,
            name='depth_inference')
        cropper_pipeline = CROPPER_PIPELINE(
            inner_pipeline=(f'{depth_pipeline}'),
            so_path=self.post_process_so_cropper,
            function_name=self.cropper_post_function_name,
            internal_offset=True
        )
        user_callback_pipeline = USER_CALLBACK_PIPELINE()
        display_pipeline = DISPLAY_PIPELINE(video_sink=self.video_sink, sync=self.sync, show_fps=self.show_fps)
    
        return (
            f'{source_pipeline} ! '
            f'{detection_pipeline_wrapper} ! '
            f'{tracker_pipeline} ! '
            f'{cropper_pipeline} ! '
            f'{user_callback_pipeline} ! '
            f'{display_pipeline}'
        )
