import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gtk, Gdk, GdkX11, GstVideo
from gi.repository import Gst, GLib
import os
import argparse
import multiprocessing
import numpy as np
import setproctitle
import cv2
import time
import hailo
import threading
import logging
from hailo_rpi_common import (
    get_default_parser,
    QUEUE,
    get_caps_from_pad,
    get_numpy_from_buffer,
    GStreamerApp,
    app_callback_class,
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.new_variable = 42  # New variable example

    def new_function(self):  # New function example
        return "The meaning of life is: "

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"

    format, width, height = get_caps_from_pad(pad)

    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        frame = get_numpy_from_buffer(buffer, format, width, height)

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    detection_count = 0
    for detection in detections:
        label = detection.get_label()
        confidence = detection.get_confidence()
        if label == "person":
            string_to_print += f"Detection: {label} {confidence:.2f}\n"
            detection_count += 1
            logger.info(string_to_print)
    
    if user_data.use_frame:
        cv2.putText(frame, f"Detections: {detection_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    #logger.info(string_to_print)
    return Gst.PadProbeReturn.OK

# -----------------------------------------------------------------------------------------------
# User Gstreamer Application
# -----------------------------------------------------------------------------------------------
class GStreamerDetectionApp(GStreamerApp):
    def __init__(self, args, user_data):
        super().__init__(args, user_data)
        self.window = None
        self.batch_size = 2
        self.network_width = 640
        self.network_height = 640
        self.network_format = "RGB"
        self.nms_score_threshold = 0.3
        self.nms_iou_threshold = 0.45
        self.max_retries = 5
        self.retry_delay = 5  # seconds
        self.watchdog_interval = 30  # seconds
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.last_frame_count = 0
        self.restart_in_progress = False

        new_postprocess_path = os.path.join(self.current_path, '../resources/libyolo_hailortpp_post.so')
        self.default_postprocess_so = new_postprocess_path if os.path.exists(new_postprocess_path) else os.path.join(self.postprocess_dir, 'libyolo_hailortpp_post.so')

        self.hef_path = args.hef_path if args.hef_path else self.get_hef_path(args.network)

        self.labels_config = f' config-path={args.labels_json} ' if args.labels_json else ''

        self.app_callback = app_callback

        self.thresholds_str = (
            f"nms-score-threshold={self.nms_score_threshold} "
            f"nms-iou-threshold={self.nms_iou_threshold} "
            f"output-format-type=HAILO_FORMAT_TYPE_FLOAT32"
        )

        setproctitle.setproctitle("Hailo Detection App")


    def get_hef_path(self, network):
        if network == "yolov6n":
            return os.path.join(self.current_path, '../resources/yolov6n.hef')
        elif network == "yolov8s":
            return os.path.join(self.current_path, '../resources/yolov8s_h8l.hef')
        elif network == "yolox_s_leaky":
            return os.path.join(self.current_path, '../resources/yolox_s_leaky_h8l_mz.hef')
        else:
            raise ValueError("Invalid network type")

    def get_pipeline_string(self):
        if self.source_type == "rpi":
            source_element = (
                "libcamerasrc name=src_0 auto-focus-mode=2 ! "
                f"video/x-raw, format={self.network_format}, width=1536, height=864 ! "
                + QUEUE("queue_src_scale")
                + "videoscale ! "
                f"video/x-raw, format={self.network_format}, width={self.network_width}, height={self.network_height}, framerate=30/1 ! "
            )
        elif self.source_type == "usb":
            source_element = (
                f"v4l2src device={self.video_source} name=src_0 ! "
                "video/x-raw, width=640, height=480, framerate=30/1 ! "
            )
        elif self.video_source.startswith("rtsp://"):
            source_element = (
                f"rtspsrc name=src_0 location={self.video_source} "
                "protocols=tcp+udp latency=2000 "
                "retry=5 timeout=5000000 tcp-timeout=5000000 "
                "drop-on-latency=true do-retransmission=false "
                "buffer-mode=auto "
                "! rtph265depay ! h265parse ! avdec_h265 "
                "! videorate ! videoconvert ! videoscale "
                f"! video/x-raw, format=RGB, width={self.network_width}, height={self.network_height} ! "
            )
        else:
            source_element = (
                f"filesrc location={self.video_source} name=src_0 ! "
                + QUEUE("queue_dec264")
                + " qtdemux ! h264parse ! avdec_h264 max-threads=2 ! "
                " video/x-raw, format=I420 ! "
            )
        source_element += QUEUE("queue_scale")
        source_element += "videoscale n-threads=2 ! "
        source_element += QUEUE("queue_src_convert")
        source_element += "videoconvert n-threads=3 name=src_convert qos=false ! "
        source_element += f"video/x-raw, format={self.network_format}, width={self.network_width}, height={self.network_height}, pixel-aspect-ratio=1/1 ! "

        pipeline_string = (
            "hailomuxer name=hmux "
            + source_element
            + "tee name=t ! "
            + QUEUE("bypass_queue", max_size_buffers=20)
            + "hmux.sink_0 "
            + "t. ! "
            + QUEUE("queue_hailonet")
            + "videoconvert n-threads=3 ! "
            f"hailonet hef-path={self.hef_path} batch-size={self.batch_size} {self.thresholds_str} force-writable=true ! "
            + QUEUE("queue_hailofilter")
            + f"hailofilter so-path={self.default_postprocess_so} {self.labels_config} qos=false ! "
            + QUEUE("queue_hmuc")
            + "hmux.sink_1 "
            + "hmux. ! "
            + QUEUE("queue_hailo_python")
            + QUEUE("queue_user_callback")
            + "identity name=identity_callback ! "
            + QUEUE("queue_hailooverlay")
            + "hailooverlay ! "
            + QUEUE("queue_videoconvert")
            + "videoconvert n-threads=3 qos=false ! "
            + QUEUE("queue_hailo_display")
            + "ximagesink name=sink"
        )
        logger.debug(f"Pipeline string: {pipeline_string}")
        return pipeline_string

    def start_watchdog(self):
        threading.Thread(target=self.watchdog_thread, daemon=True).start()

    def watchdog_thread(self):
        while True:
            time.sleep(self.watchdog_interval)
            if self.frame_count == self.last_frame_count and not self.restart_in_progress:
                logger.warning("No new frames received. Restarting pipeline...")
                self.restart_pipeline()
            self.last_frame_count = self.frame_count 
    def restart_pipeline(self):
        if self.restart_in_progress:
            logger.warning("Restart already in progress, skipping...")
            return

        self.restart_in_progress = True
        try:
            logger.info("Stopping pipeline...")
            self.pipeline.set_state(Gst.State.NULL)
            time.sleep(2)  # Give some time for cleanup

            logger.info("Recreating pipeline...")
            self.create_pipeline()
            time.sleep(2)  # Give some time for setup

            logger.info("Starting pipeline...")
            self.pipeline.set_state(Gst.State.PLAYING)
            self.add_probe()  # Re-add the probe after recreating the pipeline
        except Exception as e:
            logger.error(f"Error during pipeline restart: {e}")
        finally:
            self.restart_in_progress = False
    def add_probe(self):
        identity_callback = self.pipeline.get_by_name("identity_callback")
        if identity_callback:
            pad = identity_callback.get_static_pad("src")
            if pad:
                pad.add_probe(Gst.PadProbeType.BUFFER, self.probe_callback, self.user_data)
            else:
                logger.error("Failed to get pad from identity_callback")
        else:
            logger.error("Failed to get identity_callback element")
    def probe_callback(self, pad, info, user_data):
        self.frame_count += 1
        self.last_frame_time = time.time()
        return self.app_callback(pad, info, user_data)
    def run(self):
        self.start_watchdog()
        self.create_window()
        for attempt in range(self.max_retries):
            try:
                self.create_pipeline()
                self.add_probe()
                
                # Get the ximagesink element and set its window handle
                sink = self.pipeline.get_by_name('sink')
                self.video_area.realize()
                xid = self.video_area.get_window().get_xid()
                sink.set_window_handle(xid)
                
                self.pipeline.set_state(Gst.State.PLAYING)
                Gtk.main()
                break
            except GLib.Error as e:
                if "Could not read from resource" in str(e) and attempt < self.max_retries - 1:
                    logger.error(f"RTSP connection failed. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Unhandled error: {e}")
                    raise
    def quit(self):
        self.pipeline.set_state(Gst.State.NULL)
        if hasattr(self, 'loop') and self.loop.is_running():
            self.loop.quit()
    def create_window(self):
        self.window = Gtk.Window(title="Hailo Detection App")
        self.window.connect("delete-event", self.on_window_close)
        self.window.set_default_size(640, 640)  # Set your desired size

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(box)

        self.video_area = Gtk.DrawingArea()
        box.pack_start(self.video_area, True, True, 0)

        self.window.show_all()
    def on_window_close(self, *args):
        self.quit()
        Gtk.main_quit()
        return False
if __name__ == "__main__":
    Gtk.init(None)
    user_data = user_app_callback_class()
    parser = get_default_parser()
    parser.add_argument(
        "--network",
        default="yolov6n",
        choices=['yolov6n', 'yolov8s', 'yolox_s_leaky'],
        help="Which Network to use, default is yolov6n",
    )
    parser.add_argument(
        "--hef-path",
        default=None,
        help="Path to HEF file",
    )
    parser.add_argument(
        "--labels-json",
        default=None,
        help="Path to costume labels JSON file",
    )
    args = parser.parse_args()
    app = GStreamerDetectionApp(args, user_data)
    app.run()
