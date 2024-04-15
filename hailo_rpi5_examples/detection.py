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

# Try to import hailo python module
try:
    import hailo
except ImportError:
    exit("Failed to import hailo python module. Make sure you are in hailo virtual environment.")
from hailo_common_funcs import get_numpy_from_buffer, disable_qos

# -----------------------------------------------------------------------------------------------
# User defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# a sample class to be used in the callback function alowwing to count the number of frames
class app_callback_class:
    def __init__(self):
        self.frame_count = 0
        self.use_frame = False
        self.frame_queue = multiprocessing.Queue(maxsize=3)
        self.running = True

    def increment(self):
        self.frame_count += 1

    def get_count(self):
        return self.frame_count 

    def set_frame(self, frame):
        if not self.frame_queue.full():
            self.frame_queue.put(frame)

        
    def get_frame(self):
        if not self.frame_queue.empty():
            return self.frame_queue.get()
        else:
            return None

# Create an instance of the class
user_data = app_callback_class()

# -----------------------------------------------------------------------------------------------
# User defined callback function
# -----------------------------------------------------------------------------------------------

# This is the callback function that will be called when data is available from the pipeline

def app_callback(pad, info, user_data):
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK
        
    # using the user_data to count the number of frames
    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"
    
    caps = pad.get_current_caps()
    if caps:
        # We can now extract information from the caps
        structure = caps.get_structure(0)
        if structure:
            # Extracting some common properties
            format = structure.get_value('format')
            width = structure.get_value('width')
            height = structure.get_value('height')
            # string_to_print += (f"Frame format: {format}, width: {width}, height: {height}\n")
                    
    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if user_data.use_frame:
        # get video frame
        frame = get_numpy_from_buffer(buffer, format, width, height)
    
    # get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    
    # parse the detections
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
        if label == "person":
            string_to_print += (f"Detection: {label} {confidence:.2f}\n")
    
    if user_data.use_frame:
        # Note: using imshow will not work here, as the callback function is not running in the main thread
    	# Convert the frame to BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    print(string_to_print)
    return Gst.PadProbeReturn.OK
    # Additional option is Gst.PadProbeReturn.DROP to drop the buffer not passing in to the rest of the pipeline
    # See more options in Gstreamer documentation

# This function is used to display the user data frame
def display_user_data_frame(user_data):
    while user_data.running:
        frame = user_data.get_frame()
        if frame is not None:
            cv2.imshow("User Frame", frame)
            cv2.waitKey(1)
        time.sleep(0.02)
    

# -----------------------------------------------------------------------------------------------
# Do not edit below this line
# -----------------------------------------------------------------------------------------------

# Default parameters

network_width = 640
network_height = 640
network_format = "RGB"
video_sink = "xvimagesink"
batch_size = 1

# If TAPPAS version is 3.26.0 or higher, use the following parameters:
nms_score_threshold=0.3 
nms_iou_threshold=0.45
thresholds_str=f"nms-score-threshold={nms_score_threshold} nms-iou-threshold={nms_iou_threshold} output-format-type=HAILO_FORMAT_TYPE_FLOAT32"
# else (TAPPAS version is 3.25.0)
# thresholds_str=""

def parse_arguments():
    parser = argparse.ArgumentParser(description="Detection App")
    parser.add_argument("--input", "-i", type=str, default="/dev/video0", help="Input source. Can be a file, USB or RPi camera (CSI camera module). \
                        For RPi camera use '-i rpi'. \
                        Defaults to /dev/video0")
    parser.add_argument("--use-frame", "-u", action="store_true", help="Use frame from the callback function")
    parser.add_argument("--show-fps", "-f", action="store_true", help="Print FPS on sink")
    parser.add_argument("--disable-sync", action="store_true", help="Disables display sink sync, will run as fast possible. Relevant when using file source.")
    parser.add_argument("--dump-dot", action="store_true", help="Dump the pipeline graph to a dot file pipeline.dot")
    return parser.parse_args()

def QUEUE(name, max_size_buffers=3, max_size_bytes=0, max_size_time=0):
    return f"queue name={name} max-size-buffers={max_size_buffers} max-size-bytes={max_size_bytes} max-size-time={max_size_time} ! "

def get_source_type(input_source):
    # This function will return the source type based on the input source
    # return values can be "file", "mipi" or "usb"
    if input_source.startswith("/dev/video"):
        # check if the device is available

        return 'usb'
    else:
        if input_source.startswith("rpi"):
            return 'rpi'
        else:
            return 'file'
  

class GStreamerApp:
    def __init__(self, args):
        # Set the process title
        setproctitle.setproctitle("Hailo Detection App")
        
        # Create an empty options menu
        self.options_menu = args
        
        # Initialize variables
        tappas_workspace = os.environ.get('TAPPAS_WORKSPACE', '')
        if tappas_workspace == '':
            print("TAPPAS_WORKSPACE environment variable is not set. Please set it to the path of the TAPPAS workspace.")
            exit(1)
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.postprocess_dir = os.path.join(tappas_workspace, 'apps/h8/gstreamer/libs/post_processes')
        self.default_postprocess_so = os.path.join(self.postprocess_dir, 'libyolo_hailortpp_post.so')
        self.video_source = self.options_menu.input
        self.source_type = get_source_type(self.video_source)
        self.hef_path = os.path.join(self.current_path, '../resources/yolov5m_wo_spp_60p.hef')
        
        # Set user data parameters
        user_data.use_frame = self.options_menu.use_frame

        if (self.options_menu.disable_sync or self.source_type != "file"):
            self.sync = "false" 
        else:
            self.sync = "true"
        
        if (self.options_menu.dump_dot):
            os.environ["GST_DEBUG_DUMP_DOT_DIR"] = self.current_path
        
        # Initialize GStreamer
        
        Gst.init(None)
        
        # Create a GStreamer pipeline 
        self.pipeline = self.create_pipeline()
        
        # connect to hailo_display fps-measurements
        if (self.options_menu.show_fps):
            print("Showing FPS")
            self.pipeline.get_by_name("hailo_display").connect("fps-measurements", self.on_fps_measurement)

        # Create a GLib Main Loop
        self.loop = GLib.MainLoop()
    
    def on_fps_measurement(self, sink, fps, droprate, avgfps):
        print(f"FPS: {fps:.2f}, Droprate: {droprate:.2f}, Avg FPS: {avgfps:.2f}")
        return True

    def create_pipeline(self):
        pipeline_string = self.get_pipeline_string()
        try:
            pipeline = Gst.parse_launch(pipeline_string)
        except Exception as e:
            print(e)
            print(pipeline_string)
            exit(1)
        return pipeline

    def bus_call(self, bus, message, loop):
        t = message.type
        if t == Gst.MessageType.EOS:
            print("End-of-stream")
            loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}, {debug}")
            loop.quit()
        return True
    
    
    def get_pipeline_string(self):
        if (self.source_type == "rpi"):
            source_element = f"libcamerasrc name=src_0 auto-focus-mode=2 ! "
            source_element += f"video/x-raw, format={network_format}, width=1536, height=864 ! "
            source_element += QUEUE("queue_src_scale")
            source_element += f"videoscale ! "
            source_element += f"video/x-raw, format={network_format}, width={network_width}, height={network_height}, framerate=30/1 ! "
        
        elif (self.source_type == "usb"):
            source_element = f"v4l2src device={self.video_source} name=src_0 ! "
            source_element += f"video/x-raw, width=640, height=480, framerate=30/1 ! "
        else:  
            source_element = f"filesrc location={self.video_source} name=src_0 ! "
            source_element += QUEUE("queue_dec264")
            source_element += f" qtdemux ! h264parse ! avdec_h264 max-threads=2 ! "
            source_element += f" video/x-raw,format=I420 ! "
        source_element += QUEUE("queue_scale")
        source_element += f" videoscale n-threads=2 ! "
        source_element += QUEUE("queue_src_convert")
        source_element += f" videoconvert n-threads=3 name=src_convert ! "
        source_element += f"video/x-raw, format={network_format}, width={network_width}, height={network_height}, pixel-aspect-ratio=1/1 ! "
        
        
        pipeline_string = "hailomuxer name=hmux "
        pipeline_string += source_element
        pipeline_string += "tee name=t ! "
        pipeline_string += QUEUE("bypass_queue", max_size_buffers=20) + "hmux.sink_0 "
        pipeline_string += "t. ! " + QUEUE("queue_hailonet")
        pipeline_string += "videoconvert n-threads=3 ! "
        pipeline_string += f"hailonet hef-path={self.hef_path} batch-size={batch_size} {thresholds_str} force-writable=true ! "
        pipeline_string += QUEUE("queue_hailofilter")
        pipeline_string += f"hailofilter so-path={self.default_postprocess_so} qos=false ! "
        pipeline_string += QUEUE("queue_hmuc") + " hmux.sink_1 "
        pipeline_string += "hmux. ! " + QUEUE("queue_hailo_python")
        pipeline_string += QUEUE("queue_user_callback")
        pipeline_string += f"identity name=identity_callback ! "
        pipeline_string += QUEUE("queue_hailooverlay")
        pipeline_string += f"hailooverlay ! "
        pipeline_string += QUEUE("queue_videoconvert")
        pipeline_string += f"videoconvert n-threads=3 ! "
        pipeline_string += QUEUE("queue_hailo_display")
        pipeline_string += f"fpsdisplaysink video-sink={video_sink} name=hailo_display sync={self.sync} text-overlay={self.options_menu.show_fps} signal-fps-measurements=true "
        print(pipeline_string)
        return pipeline_string
    
    def dump_dot_file(self):
        print("Dumping dot file...")
        Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, "pipeline")
        return False
    
    def run(self):

        # Add a watch for messages on the pipeline's bus
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_call, self.loop)

        # Connect pad probe to the identity element
        identity = self.pipeline.get_by_name("identity_callback")
        identity_pad = identity.get_static_pad("src")
        identity_pad.add_probe(Gst.PadProbeType.BUFFER, app_callback, user_data)
        
        # get xvimagesink element and disable qos
        # xvimagesink is instantiated by fpsdisplaysink
        hailo_display = self.pipeline.get_by_name("hailo_display")
        xvimagesink = hailo_display.get_by_name("xvimagesink0")
        xvimagesink.set_property("qos", False)
        
        # Disable QoS to prevent frame drops
        disable_qos(self.pipeline)

        
        # Set Timed callback to display user data frame
        if (self.options_menu.use_frame):
            GLib.timeout_add_seconds(0.03, display_user_data_frame, user_data)

        # Set pipeline to PLAYING state
        self.pipeline.set_state(Gst.State.PLAYING)
        
        # dump dot file
        if (self.options_menu.dump_dot):
            GLib.timeout_add_seconds(3, self.dump_dot_file)
        
        # Run the GLib event loop
        try:
            self.loop.run()
        except:
            pass

        # Clean up
        self.pipeline.set_state(Gst.State.NULL)

# Example usage
if __name__ == "__main__":
    args = parse_arguments()
    app = GStreamerApp(args)
    app.run()
