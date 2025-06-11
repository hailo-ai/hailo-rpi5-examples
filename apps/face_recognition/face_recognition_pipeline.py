# region imports
# Standard library imports
import os
import json
import time
import threading
import queue
import signal
import uuid
import setproctitle
import multiprocessing

# Third-party imports
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import cv2
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for interactive display
import matplotlib.pyplot as plt

# Local application-specific imports
import hailo
try:
    from hailo_core.hailo_common.db_handler import DatabaseHandler, Record
except ImportError:
    from hailo_apps_infra.hailo_core.hailo_common.db_handler import DatabaseHandler, Record
try:
    from hailo_core.hailo_common.db_visualizer import DatabaseVisualizer
except ImportError:
    from hailo_apps_infra.hailo_core.hailo_common.db_visualizer import DatabaseVisualizer
try:
    from hailo_core.hailo_common.core import get_default_parser, detect_hailo_arch, get_resource_path, FIFODropQueue
except ImportError:
    from hailo_apps_infra.hailo_core.hailo_common.core import get_default_parser, detect_hailo_arch, get_resource_path, FIFODropQueue
try:
    from hailo_core.hailo_common.defines import (
        RESOURCES_SO_DIR_NAME, 
        FACE_DETECTION_PIPELINE, 
        FACE_RECOGNITION_PIPELINE, 
        RESOURCES_MODELS_DIR_NAME, 
        FACE_DETECTION_POSTPROCESS_SO_FILENAME, 
        FACE_RECOGNITION_POSTPROCESS_SO_FILENAME, 
        FACE_ALIGN_POSTPROCESS_SO_FILENAME, 
        FACE_CROP_POSTPROCESS_SO_FILENAME,
        RESOURCES_VIDEOS_DIR_NAME,
        FACE_RECOGNITION_VIDEO_NAME,
        FACE_RECON_DIR_NAME,
        FACE_RECON_TRAIN_DIR_NAME,
        FACE_RECON_SAMPLES_DIR_NAME,
        RESOURCES_JSON_DIR_NAME,
        FACE_DETECTION_JSON_NAME,
        FACE_ALGO_PARAMS_JSON_NAME
    )
except ImportError:
    from hailo_apps_infra.hailo_core.hailo_common.defines import (
    RESOURCES_SO_DIR_NAME, 
    FACE_DETECTION_PIPELINE, 
    FACE_RECOGNITION_PIPELINE, 
    RESOURCES_MODELS_DIR_NAME, 
    FACE_DETECTION_POSTPROCESS_SO_FILENAME, 
    FACE_RECOGNITION_POSTPROCESS_SO_FILENAME, 
    FACE_ALIGN_POSTPROCESS_SO_FILENAME, 
    FACE_CROP_POSTPROCESS_SO_FILENAME,
    RESOURCES_VIDEOS_DIR_NAME,
    FACE_RECOGNITION_VIDEO_NAME,
    FACE_RECON_DIR_NAME,
    FACE_RECON_TRAIN_DIR_NAME,
    FACE_RECON_SAMPLES_DIR_NAME,
    RESOURCES_JSON_DIR_NAME,
    FACE_DETECTION_JSON_NAME,
    FACE_ALGO_PARAMS_JSON_NAME
)
try:
    from hailo_core.hailo_common.buffer_utils import get_numpy_from_buffer_efficient, get_caps_from_pad
except ImportError:
    from hailo_apps_infra.hailo_core.hailo_common.buffer_utils import get_numpy_from_buffer_efficient, get_caps_from_pad
try:
    from hailo_apps.hailo_gstreamer.gstreamer_helper_pipelines import (
        SOURCE_PIPELINE,
        INFERENCE_PIPELINE,
        INFERENCE_PIPELINE_WRAPPER,
        TRACKER_PIPELINE,
        USER_CALLBACK_PIPELINE,
        DISPLAY_PIPELINE,
        CROPPER_PIPELINE,
        UI_APPSINK_PIPELINE,
        QUEUE
    )
except ImportError:
    from hailo_apps_infra.hailo_apps.hailo_gstreamer.gstreamer_helper_pipelines import (
        SOURCE_PIPELINE,
        INFERENCE_PIPELINE,
        INFERENCE_PIPELINE_WRAPPER,
        TRACKER_PIPELINE,
        USER_CALLBACK_PIPELINE,
        DISPLAY_PIPELINE,
        CROPPER_PIPELINE,
        UI_APPSINK_PIPELINE,
        QUEUE
    )
try:
    from hailo_apps.hailo_gstreamer.gstreamer_app import GStreamerApp
except ImportError:
    from hailo_apps_infra.hailo_apps.hailo_gstreamer.gstreamer_app import GStreamerApp
# endregion

class GStreamerFaceRecognitionApp(GStreamerApp):
    def __init__(self, app_callback, user_data, parser=None):
        setproctitle.setproctitle("Hailo Face Recognition App")
        if parser == None:
            parser = get_default_parser()
        parser.add_argument("--mode", default='run', help="The mode of the application: run, train, delete")
        parser.add_argument("--visualize", action="store_true", help="In run mode & CLI only, whether display the live visualization of the embeddings")
        parser.add_argument("--ui", action="store_true", help="Whether display the Gradio UI or just CLI")
        super().__init__(parser, user_data)

        # Initialize the database and table
        self.db_handler = DatabaseHandler(db_name='persons.db', table_name='persons', schema=Record)
        self.embedding_queue = multiprocessing.Queue()  # Create a queue for sending embeddings to the visualization process

        # Criteria for when a candidate frame is good enough to try recognize a person from it (e.g., skip the first few frames since in them person only entered the frame and usually is blurry)
        self.json_file = open(get_resource_path(pipeline_name=None, resource_type=RESOURCES_JSON_DIR_NAME, model=FACE_ALGO_PARAMS_JSON_NAME), "r+")
        self.algo_params = json.load(self.json_file)
        # 1. The new face has at least self.min_face_pixels_tolerance number of pixels
        self.min_face_pixels_tolerance = self.algo_params['min_face_pixels_tolerance']
        # 2. The new face is not too blurry - blurriness measurement higher (sharper image) than self.blurriness_tolerance
        self.blurriness_tolerance = self.algo_params['blurriness_tolerance']
        # 3. Ratios between landmarks ignoring translation - "Procrustes Distance" (lower is better)
        self.procrustes_distance_threshold = self.algo_params['procrustes_distance_threshold']
        # 4. How many frames to skip between detection attempts: avoid porocessing first frames since usually they are blurry since person just entered the frame, see self.track_id_frame_count
        self.skip_frames = self.algo_params['skip_frames']
        # Both for face detection & recognition networks (not tunable from the UI)
        self.batch_size = self.algo_params['batch_size']

        # Determine the architecture if not specified
        if self.options_menu.arch is None:
            detected_arch = detect_hailo_arch()
            if detected_arch is None:
                raise ValueError("Could not auto-detect Hailo architecture. Please specify --arch manually.")
            self.arch = detected_arch
        else:
            self.arch = self.options_menu.arch
        
        if self.video_source == 'resources/videos/example.mp4':
            self.video_source = get_resource_path(pipeline_name=None, resource_type=RESOURCES_VIDEOS_DIR_NAME, model=FACE_RECOGNITION_VIDEO_NAME)
        
        self.train_images_dir = get_resource_path(pipeline_name=None, resource_type=FACE_RECON_DIR_NAME, model=FACE_RECON_TRAIN_DIR_NAME) 
        self.current_file = None  # for train mode
        self.processed_names = set()  # ((key-name, val-global_id)) for train mode - pipeline will be playing for 2 seconds, so we need to ensure each person will be processed only once
        self.processed_files = set()  # for train mode - pipeline will be playing for 2 seconds, so we need to ensure each file will be processed only once

        # Set the HEF file path based on the arch
        self.hef_path_detection = get_resource_path(pipeline_name=FACE_DETECTION_PIPELINE, resource_type=RESOURCES_MODELS_DIR_NAME)
        self.hef_path_recognition = get_resource_path(pipeline_name=FACE_RECOGNITION_PIPELINE, resource_type=RESOURCES_MODELS_DIR_NAME)
        if self.arch == "hailo8":
            self.detection_func = "scrfd_10g_letterbox"
        else:  # hailo8l
            self.detection_func = "scrfd_2_5g_letterbox"
        self.recognition_func = "filter"
        self.cropper_func = "face_recognition"

        # Set the post-processing shared object file
        self.post_process_so_scrfd = get_resource_path(pipeline_name=None, resource_type=RESOURCES_SO_DIR_NAME, model=FACE_DETECTION_POSTPROCESS_SO_FILENAME)
        self.post_process_so_face_recognition = get_resource_path(pipeline_name=None, resource_type=RESOURCES_SO_DIR_NAME, model=FACE_RECOGNITION_POSTPROCESS_SO_FILENAME)
        self.post_process_so_face_align = get_resource_path(pipeline_name=None, resource_type=RESOURCES_SO_DIR_NAME, model=FACE_ALIGN_POSTPROCESS_SO_FILENAME)
        self.post_process_so_cropper = get_resource_path(pipeline_name=None, resource_type=RESOURCES_SO_DIR_NAME, model=FACE_CROP_POSTPROCESS_SO_FILENAME)
        
        # Callbacks: bindings between the C++ & Python code
        self.app_callback = app_callback
        self.vector_db_callback_name = "vector_db_callback"
        self.train_vector_db_callback_name = "train_vector_db_callback"
        self.create_pipeline()  # initialize self.pipeline
        if self.options_menu.mode == 'run':
            self.plot_thread = None
            self.connect_vector_db_callback()
            if self.options_menu.ui:
                self.webrtc_frames_queue = FIFODropQueue(maxsize=2)  # smaller sizes are better for live stream
                app_sink = self.pipeline.get_by_name('ui_appsink')
                app_sink.set_property('emit-signals', True)
                app_sink.connect('new-sample', self.appsink_callback)
        else:  # train
            self.connect_train_vector_db_callback()
        self.trac_id_to_global_id = {}  # association between tracker id and global id for tracker pipeline element
        self.track_id_frame_count = {}  # Dictionary to track frame counts for each track ID - avoid porocessing first frames since usually they are blurry since person just entered the frame 

        self.visualization_process = None # Process for displaying the matplotlib embedding visualization in a separate process

        # region worker queue threads for saving images
        # Create a queue to hold the tasks
        self.task_queue = queue.Queue()

        # Define the worker function
        def worker():
            while True:  # while pipeline playing
                task = self.task_queue.get()
                if task is None:  # Exit signal
                    break

                # Check the task type and process accordingly
                if task['type'] == 'save_image':
                    frame, image_path = task['frame'], task['image_path']
                    self.save_image_file(frame, image_path)
                elif task['type'] == 'send_notification':
                    user_data.send_notification(
                        name=task['name'],
                        global_id=task['global_id'],
                        distance=task['distance'],
                        frame=task['frame']
                    )
                self.task_queue.task_done()

        # Start worker threads
        self.num_worker_threads = 1
        self.threads = []
        for i in range(self.num_worker_threads):
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()
            self.threads.append(t)
        # endregion
        
    def get_pipeline_string(self):
        source_pipeline = SOURCE_PIPELINE(self.video_source, self.video_width, self.video_height, frame_rate=self.frame_rate, sync=self.sync)
        detection_pipeline = INFERENCE_PIPELINE(hef_path=self.hef_path_detection, post_process_so=self.post_process_so_scrfd, post_function_name=self.detection_func, batch_size=self.batch_size, config_json=get_resource_path(pipeline_name=None, resource_type=RESOURCES_JSON_DIR_NAME, model=FACE_DETECTION_JSON_NAME))
        detection_pipeline_wrapper = INFERENCE_PIPELINE_WRAPPER(detection_pipeline)
        tracker_pipeline = TRACKER_PIPELINE(class_id=-1, kalman_dist_thr=0.7, iou_thr=0.8, init_iou_thr=0.9, keep_new_frames=2, keep_tracked_frames=6, keep_lost_frames=8, keep_past_metadata=True, name='hailo_face_tracker')
        mobile_facenet_pipeline = INFERENCE_PIPELINE(hef_path=self.hef_path_recognition, post_process_so=self.post_process_so_face_recognition, post_function_name=self.recognition_func, batch_size=self.batch_size, config_json=None, name='face_recognition_inference')
        cropper_pipeline = CROPPER_PIPELINE(inner_pipeline=(f'hailofilter so-path={self.post_process_so_face_align} '
                                                            f'name=face_align_hailofilter use-gst-buffer=true qos=false ! '
                                                            f'{QUEUE(name="detector_pos_face_align_q")} ! '
                                                            f'{mobile_facenet_pipeline}'),
                                            so_path=self.post_process_so_cropper, function_name=self.cropper_func, internal_offset=True)
        vector_db_callback_pipeline = USER_CALLBACK_PIPELINE(name=self.vector_db_callback_name)  # 'identity name' - is a GStreamer element that does nothing, but allows to add a probe to it
        user_callback_pipeline = USER_CALLBACK_PIPELINE()
        if self.options_menu.ui:
            display_pipeline = UI_APPSINK_PIPELINE(name='ui_appsink')
        else:
            display_pipeline = DISPLAY_PIPELINE(video_sink=self.video_sink, sync=self.sync, show_fps=self.show_fps)

        if self.options_menu.mode == 'train':
            source_pipeline = (f"multifilesrc location={self.current_file} loop=true num-buffers=30 ! "  # each image 30 times
                               f"decodebin ! videoconvert n-threads=4 qos=false ! video/x-raw, format=RGB, pixel-aspect-ratio=1/1 ")
            vector_db_callback_pipeline = USER_CALLBACK_PIPELINE(name=self.train_vector_db_callback_name)
            display_pipeline = DISPLAY_PIPELINE(video_sink=self.video_sink, sync=self.sync, show_fps=self.show_fps)

        return (
            f'{source_pipeline} ! '
            f'{detection_pipeline_wrapper} ! '
            f'{tracker_pipeline} ! '
            f'{cropper_pipeline} ! '
            f'{vector_db_callback_pipeline} ! '
            f'{user_callback_pipeline} ! '
            f'{display_pipeline}'
        )
    
    def run(self):
        if self.options_menu.mode == 'run':
            if self.options_menu.visualize and not self.options_menu.ui:  # Start the visualization in a separate process
                self.start_visualization_process()
            super().run()  # start the Gstreamer pipeline
        else:  # train
            self.run_training()

    def run_training(self):
        """
        Iterates over the training folder structured with subfolders (person names),
        generates embeddings for each image, and stores them in the database with the person's name.
        """
        print(f"Training on images from {self.train_images_dir}")
        for person_name in os.listdir(self.train_images_dir):  # Iterate over subfolders in the training directory
            person_folder = os.path.join(self.train_images_dir, person_name)
            if self.db_handler.get_record_by_label(label=person_name):  # Ensure the person exists in the database, or create a new record
                continue
            if not os.path.isdir(person_folder):  # Skip if not a directory
                continue
            print(f"Processing person: {person_name}")
            for image_file in os.listdir(person_folder):  # Iterate over images in the person's folder
                print(f"Processing image: {image_file}")
                self.current_file = os.path.join(person_folder, image_file)  # Set the current file for pipeline processing, used internally in get_pipeline_string
                self.create_pipeline()  # Initialize the pipeline with the updated file path
                self.connect_train_vector_db_callback()  # Connect the callback after pipeline initialization
                try:  # Set the pipeline to PLAYING to process the image
                    self.pipeline.set_state(Gst.State.PLAYING)
                    time.sleep(2)  # Wait for processing to complete
                except Exception as e:
                    print(f"Error processing image {image_file}: {e}")
                finally:  # Stop and clean up the pipeline
                    if self.pipeline:
                        self.pipeline.set_state(Gst.State.NULL)
        print("Training completed")
    
    def start_visualization_process(self):
        """Start the visualization process in a separate process."""
        db_records = self.db_handler.get_all_records()  # Get a copy of the records to avoid shared memory issues
        p = multiprocessing.Process(target=self.display_visualization_process, args=(db_records, self.embedding_queue))
        p.daemon = True  # Process will terminate when the main program exits
        p.start()
        self.visualization_process = p  # Keep a reference to the process for later termination
    
    @staticmethod
    def display_visualization_process(db_records, embedding_queue):
        """Run visualization in a separate process"""
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # Ignore SIGINT in child processes
        visualizer = DatabaseVisualizer()  # Create a new visualizer in this process
        visualizer.set_db_records(db_records)
        visualizer.visualize(mode='cli')  # Initialize the plot
        while True:  # Append the new embeddings to the plot
            try:
                embedding_vector, label = embedding_queue.get(timeout=0.1)  # Get new embedding from the queue
                visualizer.add_embeddings_to_existing_plot(embeddings=[embedding_vector], labels=[label])
            except queue.Empty:  # No embedding available in the queue
                plt.pause(0.1)  # Add a small pause to prevent high CPU usage
            except Exception as e:
                print(f"Error in visualization process: {e}")
                break

    def connect_vector_db_callback(self):
        identity = self.pipeline.get_by_name(self.vector_db_callback_name)
        if identity:
            identity_pad = identity.get_static_pad("src")  # src is the output of an element
            identity_pad.add_probe(Gst.PadProbeType.BUFFER, self.vector_db_callback, self.user_data)  # trigger - when the pad gets buffer
    
    def connect_train_vector_db_callback(self):
        identity = self.pipeline.get_by_name(self.train_vector_db_callback_name)
        if identity:
            identity_pad = identity.get_static_pad("src")  # src is the output of an element
            identity_pad.add_probe(Gst.PadProbeType.BUFFER, self.train_vector_db_callback, self.user_data)  # trigger - when the pad gets buffer

    def save_image_file(self, frame, image_path):
        image = Image.fromarray(frame)  # Convert the frame to an image
        image.save(image_path, format="JPEG", quality=85)  # Save as a compressed JPEG with quality 85
    
    def measure_blurriness(self, image):
        """
        Measures the blurriness of an image using the variance of the Laplacian method.

        Args:
            image (np.ndarray): The input image.

        Returns:
            float: The variance of the Laplacian, which indicates the blurriness of the image.
        """
        return 400  # dummy implementation
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
        variance_of_laplacian = laplacian.var()
        return variance_of_laplacian

    def calculate_procrustes_distance(self, detection, width, height):
        """
        Calculates the Procrustes distance between detected landmarks and a predefined destination vector.

        Args:
            detection: The detection object containing landmarks and bounding box.
            width (int): The width of the frame.
            height (int): The height of the frame.

        Returns:
            float: The Procrustes distance.

        The Procrustes distance is a measure of similarity between two sets of points, often used in shape analysis. 
        When applied to face recognition landmarks (e.g., eyes, nose, and mouth), 
        it quantifies how similar the relative positions of these landmarks are between two faces, 
        after accounting for differences in scale, translation, and rotation.
        """
        # Extract landmarks
        landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
        if not landmarks or len(landmarks) != 1:
            return float('inf')  # Return a large value if landmarks are not available

        points = landmarks[0].get_points()
        bbox = detection.get_bbox()

        # Normalize detected landmarks to the same scale as DEST_VECTOR
        detected_landmarks = np.array([
            [
                int((point.x() * bbox.width() + bbox.xmin()) * width),
                int((point.y() * bbox.height() + bbox.ymin()) * height)
            ]
            for point in points
        ])

        # Define the destination vector - magic numbers from the algorithm
        DEST_VECTOR = np.array([
            [38.2946, 51.6963],
            [73.5318, 51.5014],
            [56.0252, 71.7366],
            [41.5493, 92.3655],
            [70.7299, 92.2041]
        ])

        # Ensure detected_landmarks is a float array
        detected_landmarks = detected_landmarks.astype(np.float64)

        # Center the landmarks
        detected_landmarks -= np.mean(detected_landmarks, axis=0)
        DEST_VECTOR -= np.mean(DEST_VECTOR, axis=0)

        # Scale the landmarks
        detected_landmarks /= np.linalg.norm(detected_landmarks)
        DEST_VECTOR /= np.linalg.norm(DEST_VECTOR)

        # Compute the Procrustes distance
        distance = np.linalg.norm(detected_landmarks - DEST_VECTOR)

        return distance

    def get_detection_num_pixels(self, bbox, frame_width, frame_height):
        bbox_width_pixels = int(bbox.width() * frame_width)
        bbox_height_pixels = int(bbox.height() * frame_height)
        return bbox_width_pixels * bbox_height_pixels
    
    def crop_frame(self, frame, bbox, width, height):
        # Retrieve the bounding box of the detection to save only the cropped area - useful in case there are more than 1 person in the frame
        # Add extra padding 0.15 to each side of the bounding box
        # Clamp the relative coordinates to the range [0, 1]
        x_min = max(0, min(bbox.xmin()-0.15, 1))
        y_min = max(0, min(bbox.ymin()-0.15, 1))
        x_max = max(0, min(bbox.xmax()+0.15, 1))
        y_max = max(0, min(bbox.ymax()+0.15, 1))

        # Scale the relative coordinates to absolute pixel values
        x_min = int(x_min * width)
        y_min = int(y_min * height)
        x_max = int(x_max * width)
        y_max = int(y_max * height)

        # Crop the frame to the detection area
        return frame[y_min:y_max, x_min:x_max]

    def shutdown(self, signum=None, frame=None):
        # Terminate the visualization process
        if hasattr(self, 'visualization_process') and self.visualization_process:
            try:
                if self.visualization_process.is_alive():
                    self.visualization_process.terminate()
                    try:
                        self.visualization_process.join(timeout=2)  # Add timeout
                    except Exception as e:
                        print(f"Error joining visualization process: {e}")
                self.visualization_process = None  # Clear the reference to prevent multiple termination attempts
            except Exception as e:
                print(f"Error terminating visualization process: {e}")
                self.visualization_process = None  # Clear reference anyway
        # Call the parent class shutdown method to clean up the GStreamer pipeline and other resources
        super().shutdown(signum=None, frame=None)  

    def add_task(self, task_type, **kwargs):
        """
        Add a task to the queue.

        Args:
            task_type (str): The type of task (e.g., 'save_image').
            kwargs: Additional arguments for the task.
        """
        task = {'type': task_type, **kwargs}
        self.task_queue.put(task)

    def get_processed_names_by_name(self, key):
        """
        Retrieve a value from the processed_names set by its key.

        Args:
            key (str): The key to search for.

        Returns:
            Any: The value associated with the key, or None if the key is not found.
        """
        for k, v in self.processed_names:
            if k == key:
                return v
        return None
    
    def is_name_processed(self, key):
        """
        Check if a key exists in the processed_names set.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        for k, _ in self.processed_names:
            if k == key:
                return True
        return False

    def vector_db_callback(self, pad, info, user_data):
        buffer = info.get_buffer()
        if buffer is None:
            return Gst.PadProbeReturn.OK
        format, width, height = get_caps_from_pad(pad)
        roi = hailo.get_roi_from_buffer(buffer)
        
        for detection in (d for d in roi.get_objects_typed(hailo.HAILO_DETECTION) if d.get_label() == 'face'):
            track_id = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id() if detection.get_objects_typed(hailo.HAILO_UNIQUE_ID) else None
            if track_id in self.trac_id_to_global_id and self.trac_id_to_global_id[track_id][1] == 'Recognized':
                continue  # if the track ID is already associated with a global ID, this detection has already been processed and positively recognized (as a person from the database)
            elif track_id in self.track_id_frame_count and track_id in self.trac_id_to_global_id and self.trac_id_to_global_id[track_id][1] == 'Unknown' and self.track_id_frame_count[track_id] < self.skip_frames:
                self.track_id_frame_count[track_id] += 1
                continue  # track ID is already associated with an unknown person, and we are still in the skip frames period, so we skip this detection
            
            embedding = detection.get_objects_typed(hailo.HAILO_MATRIX)
            if len(embedding) != 1:  # we will continue if new embedding exists
                continue  # if cropper pipeline element decided to pass the detection - it will arrive to this stage of the pipeline without face embedding
            detection.remove_object(embedding[0])  # in case the detection pointer tracker pipeline element (from earlier side of the pipeline) holds is the same as the one we have, remove the embedding, so embedding similarity won't be part of the decision criteria
            [detection.remove_object(classification) for classification in detection.get_objects_typed(hailo.HAILO_CLASSIFICATION)]  # remove all classifications from the detection, since we will add our own classification based on the embedding search result

            if self.track_id_frame_count.get(track_id, 0) < self.skip_frames:  # for new detections - process only after self.skip_frames frames
                self.track_id_frame_count[track_id] = self.track_id_frame_count.get(track_id, 0) + 1
                continue
            
            frame = get_numpy_from_buffer_efficient(buffer, format, width, height)
            cropped_frame = self.crop_frame(frame, detection.get_bbox(), width, height)

            if (self.get_detection_num_pixels(detection.get_bbox(), width, height) < self.min_face_pixels_tolerance or 
                self.calculate_procrustes_distance(detection, width, height) > self.procrustes_distance_threshold   or 
                self.measure_blurriness(cropped_frame) < self.blurriness_tolerance):
                self.track_id_frame_count[track_id] = 0
                continue  # If current frame does not meet the criteria, skip it and wait again self.skip_frames before processing the same track id
            embedding_vector = np.array(embedding[0].get_data())
            person = self.db_handler.search_record(embedding=embedding_vector)
            
            if person:
                self.trac_id_to_global_id[track_id] = (person['global_id'], 'Recognized') 
                detection.add_object(hailo.HailoClassification(type='1', label=person['label'], confidence=(1-person['_distance'])))  # type 1 = hailo.HAILO_CLASSIFICATION, Uknown person will not be added to the tracker - because after another skip_frames it will be processed again, and might be recognized as a person from the database
            else:  # If no person is found, init frame count for this track id, and give another chance to the same track id after self.skip_frames X 10
                self.trac_id_to_global_id[track_id] = (uuid.uuid4(), 'Unknown')
                self.track_id_frame_count[track_id] = -10 * self.skip_frames  
            
            if self.options_menu.visualize and person:  # If visualization is active, send the embedding to the visualization process - in case of new uknown person, don't plot - since the Uknown might be become later recognized in better frame after self.skip_frames try
                try:
                    self.embedding_queue.put((embedding_vector, person['label']), timeout=0.1)  # Use non-blocking put with a short timeout
                except:
                    pass  # Ignore if queue is full or other issues
            
            if self.user_data.telegram_enabled:  # adding task to the worker queue
                self.add_task('send_notification', name=person['label'] if person else None, global_id=self.trac_id_to_global_id[track_id], distance=person['_distance'] if person else None, frame=cropped_frame)

        return Gst.PadProbeReturn.OK
    
    def train_vector_db_callback(self, pad, info, user_data):
        if self.current_file in self.processed_files:
            return Gst.PadProbeReturn.OK
        buffer = info.get_buffer()
        if buffer is None:
            return Gst.PadProbeReturn.OK
        format, width, height = get_caps_from_pad(pad)
        frame = get_numpy_from_buffer_efficient(buffer, format, width, height)
        roi = hailo.get_roi_from_buffer(buffer)
        for detection in (d for d in roi.get_objects_typed(hailo.HAILO_DETECTION) if d.get_label() == "face"):
            embedding = detection.get_objects_typed(hailo.HAILO_MATRIX)
            if len(embedding) != 1:  # we will continue if new embedding exists - might be new person, or another image of existing person
                continue  # if cropper pipeline element decided to pass the detection - it will arrive to this stage of the pipeline without face embedding.
            detection.remove_object(embedding[0])  # in case the detection pointer tracker pipeline element (from earlier side of the pipeline) holds is the same as the one we have, remove the embedding, so embedding similarity won't be part of the decision criteria
            cropped_frame = self.crop_frame(frame, detection.get_bbox(), width, height)
            embedding_vector = np.array(embedding[0].get_data())
            image_path = os.path.join(get_resource_path(pipeline_name=None, resource_type=FACE_RECON_DIR_NAME, model=FACE_RECON_SAMPLES_DIR_NAME), f"{uuid.uuid4()}.jpeg")
            self.add_task('save_image', frame=cropped_frame, image_path=image_path)  # Add the frame to the queue for processing
            name = os.path.basename(os.path.dirname(self.current_file))
            if self.is_name_processed(name):
                self.db_handler.insert_new_sample(record=self.db_handler.get_record_by_id(self.get_processed_names_by_name(name)), embedding=embedding_vector, sample=image_path, timestamp=int(time.time())) 
                print(f"Adding face to: {name}")
            else: 
                person = self.db_handler.create_record(embedding=embedding_vector, sample=image_path, timestamp=int(time.time()), label=name)
                print(f"New person added: {person['global_id']}")
                self.processed_names.add((name, person['global_id']))
            self.processed_files.add(self.current_file)
            return Gst.PadProbeReturn.OK  # in case of training - iterate exactly once per image
        return Gst.PadProbeReturn.OK