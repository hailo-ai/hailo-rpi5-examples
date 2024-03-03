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
    
    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if user_data.use_frame:
        # get video frame
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
            
                # Instance segmentation mask from detection (if available)
                masks = detection.get_objects_typed(hailo.HAILO_CONF_CLASS_MASK)
                if len(masks) != 0:
                    mask = masks[0]
                    # Note that the mask is a 1D array, you need to reshape it to get the original shape
                    mask_height = mask.get_height()
                    mask_width = mask.get_width()
                    data = np.array(mask.get_data())
                    data = data.reshape((mask_height, mask_width))
                    # data shuold be enlarged x4
                    mask_width = mask_width * 4
                    mask_height = mask_height * 4
                    data = cv2.resize(data, (mask_width, mask_height), interpolation=cv2.INTER_NEAREST)
                    string_to_print += (f"Mask shape: {data.shape}\n")
    
    if user_data.use_frame:
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


def parse_arguments():
    parser = argparse.ArgumentParser(description="Instance segmentation App")
    parser.add_argument("--input", "-i", type=str, default="/dev/video0", help="Input source. Can be a file, USB or RPi camera (CSI camera module). \
                        For RPi camera use '-i rpi'. \
                        Defaults to /dev/video0")
    parser.add_argument("--use-frame", "-u", action="store_true", help="Use frame from the callback function")
    parser.add_argument("--show-fps", "-f", action="store_true", help="Print FPS on sink")
    parser.add_argument("--disable-sync", action="store_true", help="Disables display sink sync, will run as fast possible.")
    parser.add_argument("--dump-dot", action="store_true", help="Dump the pipeline graph to a dot file pipeline.dot")
    return parser.parse_args()

def QUEUE(name, max_size_buffers=3, max_size_bytes=0, max_size_time=0):
    return f"queue name={name} max-size-buffers={max_size_buffers} max-size-bytes={max_size_bytes} max-size-time={max_size_time} ! "

def get_source_type(input_source):
    # This function will return the source type based on the input source
    # return values can be "file", "mipi" or "usb"
    if input_source.startswith("/dev/video"):
        return 'usb'
    else:
        if input_source.startswith("rpi"):
            return 'rpi'
        else:
            return 'file'
  

class GStreamerApp:
    def __init__(self, args):
        # Set the process title
        setproctitle.setproctitle("Hailo Instance Segmentation App")
        
        # Create an empty options menu
        self.options_menu = args
        
        # Initialize variables
        tappas_workspace = os.environ.get('TAPPAS_WORKSPACE', '')
        if tappas_workspace == '':
            print("TAPPAS_WORKSPACE environment variable is not set. Please set it to the path of the TAPPAS workspace.")
            exit(1)
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.postprocess_dir = os.path.join(tappas_workspace, 'apps/h8/gstreamer/libs/post_processes')
        self.default_postprocess_so = os.path.join(self.postprocess_dir, 'libyolov5seg_post.so')
        self.default_network_name = "yolov5seg"
        self.video_source = self.options_menu.input
        self.source_type = get_source_type(self.video_source)
        self.hef_path = os.path.join(self.current_path, '../resources/yolov5n_seg.hef')
        
        # Set user data parameters
        user_data.use_frame = self.options_menu.use_frame

        if (self.options_menu.disable_sync):
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
        # QOS
        elif t == Gst.MessageType.QOS:
            # Handle QoS message here
            qos_element = message.src.get_name()
            print(f"QoS message received from {qos_element}")
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
        source_element += f" videoconvert n-threads=3 name=src_convert qos=false ! "
        source_element += f"video/x-raw, format={network_format}, width={network_width}, height={network_height}, pixel-aspect-ratio=1/1 ! "
        
        
        pipeline_string = "hailomuxer name=hmux "
        pipeline_string += source_element
        pipeline_string += "tee name=t ! "
        pipeline_string += QUEUE("bypass_queue", max_size_buffers=20) + "hmux.sink_0 "
        pipeline_string += "t. ! " + QUEUE("queue_hailonet")
        pipeline_string += "videoconvert n-threads=3 ! "
        pipeline_string += f"hailonet hef-path={self.hef_path} batch-size={batch_size} ! "
        pipeline_string += QUEUE("queue_hailofilter")
        pipeline_string += f"hailofilter function-name={self.default_network_name} so-path={self.default_postprocess_so} qos=false ! "
        pipeline_string += QUEUE("queue_hmuc") + " hmux.sink_1 "
        pipeline_string += "hmux. ! " + QUEUE("queue_hailo_python")
        pipeline_string += QUEUE("queue_user_callback")
        pipeline_string += f"identity name=identity_callback ! "
        pipeline_string += QUEUE("queue_hailooverlay")
        pipeline_string += f"hailooverlay ! "
        pipeline_string += QUEUE("queue_videoconvert")
        pipeline_string += f"videoconvert n-threads=3 qos=false ! "
        pipeline_string += QUEUE("queue_hailo_display")
        pipeline_string += f"fpsdisplaysink video-sink={video_sink} name=hailo_display sync={self.sync} text-overlay={self.options_menu.show_fps} signal-fps-measurements=true "
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
        
        # disable qos for the entire pipeline
        disable_qos(self.pipeline)

        # start a sub process to run the display_user_data_frame function
        if (self.options_menu.use_frame):
            display_process = multiprocessing.Process(target=display_user_data_frame, args=(user_data,))
            display_process.start()

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
        user_data.running = False
        self.pipeline.set_state(Gst.State.NULL)
        if (self.options_menu.use_frame):
            display_process.terminate()
            display_process.join()

# Example usage
if __name__ == "__main__":
    args = parse_arguments()
    app = GStreamerApp(args)
    app.run()
