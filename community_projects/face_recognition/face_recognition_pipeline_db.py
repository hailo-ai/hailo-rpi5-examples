# region imports
# Standard library imports
import os
import sys
import time
import threading
import queue
import signal
import subprocess
import uuid
import setproctitle

# Third-party imports
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import cv2
import numpy as np
from PIL import Image

# Local application-specific imports
import hailo
from db_handler import search_person, insert_new_face, create_person, get_person_by_id, visualize_persons, add_embedding_to_existing_plot, init_database as db_init
from hailo_apps_infra.hailo_rpi_common import (
    get_default_parser,
    detect_hailo_arch,
    get_numpy_from_buffer,
    get_caps_from_pad
)
from hailo_apps_infra.gstreamer_helper_pipelines import (
    SOURCE_PIPELINE,
    INFERENCE_PIPELINE,
    INFERENCE_PIPELINE_WRAPPER,
    TRACKER_PIPELINE,
    USER_CALLBACK_PIPELINE,
    DISPLAY_PIPELINE,
    CROPPER_PIPELINE
)
from hailo_apps_infra.gstreamer_app import GStreamerApp
# endregion

class GStreamerFaceRecognitionApp(GStreamerApp):
    def __init__(self, app_callback, user_data, parser=None):
        setproctitle.setproctitle("Hailo Face Recognition App")
        if parser == None:
            parser = get_default_parser()
        parser.add_argument("--mode", default='run', help="run, run-save, train, update, delete")
        super().__init__(parser, user_data)

        # Initialize the database and table
        self.init_database()
        
        # If for existing person there is a classification with those conditions - we will update the person's avg embedding with the new image:
        # 1. Distance better (each person has own distance based on variability of embeddings) or at least no worse than self.embedding_distance_tolerance 
        self.embedding_distance_tolerance = 0.1
        # 2. The new face has at least self.min_face_pixels_tolerance number of pixels
        self.min_face_pixels_tolerance = 60000
        # 3. The new face is not too blurry - blurriness measurement higher (sharper image) than self.blurriness_tolerance
        self.blurriness_tolerance = 300
        # 4. Maximum number of faces to keep in the database per person
        self.max_faces_per_person = 3
        # 5. Last image of a person was added to the database more than an self.last_image_sent_time ago
        self.last_image_sent_threshold_time = 0  # 1 second
        # 6. Ratios between landmarks ignoring translation - "Procrustes Distance"
        self.procrustes_distance_threshold = 0.3  # lower is better

        # Determine the architecture if not specified
        if self.options_menu.arch is None:
            detected_arch = detect_hailo_arch()
            if detected_arch is None:
                raise ValueError("Could not auto-detect Hailo architecture. Please specify --arch manually.")
            self.arch = detected_arch
        else:
            self.arch = self.options_menu.arch
        self.resources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')
        if not self.video_source:
            self.video_source = os.path.join(self.resources_path, 'face_recognition.mp4')
        
        self.check_resources_dir()
        self.images_dir = os.path.join(self.resources_path, 'train')
        self.current_file = None  # for train mode
        self.processed_names = set()  # ((key-name, val-global_id)) for train mode - pipeline will be playing for 2 seconds, so we need to ensure each person will be processed only once
        self.processed_files = set()  # for train mode - pipeline will be playing for 2 seconds, so we need to ensure each file will be processed only once
        
        # Set the HEF file path based on the arch
        if self.arch == "hailo8":
            self.hef_path_detection = os.path.join(self.resources_path, 'scrfd_10g.hef')
            self.hef_path_recognition = os.path.join(self.resources_path, 'arcface_mobilefacenet.hef')
            self.detection_func = "scrfd_10g_letterbox"
        else:  # hailo8l
            self.hef_path_detection = os.path.join(self.resources_path, 'scrfd_2.5g.hef')
            self.hef_path_recognition = os.path.join(self.resources_path, 'arcface_mobilefacenet_h8l.hef')
            self.detection_func = "scrfd_2_5g_letterbox"
        self.recognition_func = "filter"
        self.cropper_func = "face_recognition"

        # Both for face detection & recognition networks
        self.batch_size = 1

        # Set the post-processing shared object file
        self.post_process_so_scrfd = os.path.join(self.resources_path, 'libscrfd.so')
        self.post_process_so_face_recognition = os.path.join(self.resources_path, 'libface_recognition_post.so')
        self.post_process_so_face_align = os.path.join(self.resources_path, 'libvms_face_align.so ')
        self.post_process_so_cropper = os.path.join(self.resources_path,'libvms_croppers.so')
        
        # Callbacks: bindings between the C++ & Python code
        self.app_callback = app_callback
        self.vector_db_callback_name = "vector_db_callback"
        self.train_vector_db_callback_name = "train_vector_db_callback"
        self.create_pipeline()  # initialize self.pipeline
        if self.options_menu.mode in ['run', 'run-save']:
            self.connect_vector_db_callback()
        else:  # train
            self.connect_train_vector_db_callback()
        self.trac_id_to_global_id = {}  # association between tracker id and global id for tracker pipeline element

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
        self.num_worker_threads = 4
        self.threads = []
        for i in range(self.num_worker_threads):
            t = threading.Thread(target=worker)
            t.start()
            self.threads.append(t)

        # Register the signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        # endregion

    def get_pipeline_string(self):
        source_pipeline = SOURCE_PIPELINE(self.video_source, self.video_width, self.video_height)
        detection_pipeline = INFERENCE_PIPELINE(hef_path=self.hef_path_detection, post_process_so=self.post_process_so_scrfd, post_function_name=self.detection_func, batch_size=self.batch_size, config_json=os.path.join(self.resources_path, "scrfd.json"))
        detection_pipeline_wrapper = INFERENCE_PIPELINE_WRAPPER(detection_pipeline)
        tracker_pipeline = TRACKER_PIPELINE(class_id=-1, kalman_dist_thr=0.7, iou_thr=0.8, init_iou_thr=0.9, keep_new_frames=2, keep_tracked_frames=6, keep_lost_frames=8, keep_past_metadata=True, name='hailo_face_tracker')
        mobile_facenet_pipeline = INFERENCE_PIPELINE(hef_path=self.hef_path_recognition, post_process_so=self.post_process_so_face_recognition, post_function_name=self.recognition_func, batch_size=self.batch_size, config_json=None, name='face_recognition_inference')
        cropper_pipeline = CROPPER_PIPELINE(inner_pipeline=(f'hailofilter so-path={self.post_process_so_face_align} '
                                                            f'name=face_align_hailofilter use-gst-buffer=true qos=false ! '
                                                            f'queue name=detector_pos_face_align_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! '
                                                            f'{mobile_facenet_pipeline}'),
                                            so_path=self.post_process_so_cropper, function_name=self.cropper_func, internal_offset=True)
        vector_db_callback_pipeline = USER_CALLBACK_PIPELINE(name=self.vector_db_callback_name)  # 'identity name' - is a GStreamer element that does nothing, but allows to add a probe to it
        user_callback_pipeline = USER_CALLBACK_PIPELINE()
        display_pipeline = (f'hailooverlay name=hailo_overlay qos=false show-confidence=true local-gallery=false line-thickness=5 font-thickness=2 landmark-point-radius=8 ! '
                            f'queue name=hailo_post_draw leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! '
                            f'videoconvert n-threads=4 qos=false name=display_videoconvert qos=false ! '
                            f'queue name=hailo_display_q_0 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! '
                            f'fpsdisplaysink video-sink=xvimagesink name=hailo_display sync={self.sync} text-overlay={self.show_fps}')
        
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
        if self.options_menu.mode == 'run' or self.options_menu.mode == 'run-save':
            if self.options_menu.mode == 'run':
                plot_thread = threading.Thread(target=visualize_persons)  # Start the plot in a separate thread
                plot_thread.daemon = True  # Ensure the thread exits when the main program exits
                plot_thread.start()
            super().run()
        else:  # train
            self.run_training()

    def run_training(self):
        """
        Iterates over the training folder structured with subfolders (person names),
        generates embeddings for each image, and stores them in the database with the person's name.
        """
        print(f"Training on images from {self.images_dir}")
        for person_name in os.listdir(self.images_dir):  # Iterate over subfolders in the training directory
            person_folder = os.path.join(self.images_dir, person_name)
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

    def check_resources_dir(self):
        if not os.path.exists(self.resources_path):
            print(f'Resources directory not found, creating it by running ./download_resources.sh')
            result = subprocess.run([f'{os.path.dirname(os.path.abspath(__file__))}/download_resources.sh'], shell=True)
            if result.returncode != 0:
                print("Error: Failed to run ./download_resources", file=sys.stderr)
                sys.exit(1)

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

    def init_database(self):
        self.db, self.tbl = db_init()  # initializes the LanceDB database and table & ensure the database and table are initialized

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

    def signal_handler(self, sig, frame):
        # Signal handler to stop worker threads
        print(f"Received signal {sig}. Shutting down...")
        for i in range(self.num_worker_threads):
            self.task_queue.put(None)
        for t in self.threads:
            t.join()
        sys.exit(0)

    def add_task(self, task_type, **kwargs):
        """
        Add a task to the queue.

        Args:
            task_type (str): The type of task ('save_image' or 'send_notification').
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
        frame = get_numpy_from_buffer(buffer, format, width, height)
        roi = hailo.get_roi_from_buffer(buffer)
        for detection in (d for d in roi.get_objects_typed(hailo.HAILO_DETECTION) if d.get_label() == "face"):
            embedding = detection.get_objects_typed(hailo.HAILO_MATRIX)
            if len(embedding) != 1:  # we will continue if new embedding exists - might be new person, or another image of existing person
                continue  # if cropper pipeline element decided to pass the detection - it will arrive to this stage of the pipeline without face embedding. # print(f"Error: Expected 1 embedding, got {len(embedding)}")
            detection.remove_object(embedding[0])  # in case the detection pointer tracker pipeline element (from earlier side of the pipeline) holds is the same as the one we have, remove the embedding, so embedding similarity won't be part of the decision criteria
            track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
            track_id = track[0].get_id() if track else None
            if track_id in self.trac_id_to_global_id:
                continue  # if the track id is already associated with a global id - we already processed this detection, so add face can't be for same track id session anyway
            cropped_frame = self.crop_frame(frame, detection.get_bbox(), width, height)
            embedding_vector = np.array(embedding[0].get_data())
            person = search_person(embedding=embedding_vector)

            if self.options_menu.mode == 'run':  
                detection.add_object(hailo.HailoClassification(type='1', label=person['name'] if person else 'Unknown', confidence=person['_distance'] if person else 1))  # type 1 = hailo.HAILO_CLASSIFICATION
                self.trac_id_to_global_id[track_id] = uuid.uuid4() if person is None else person['global_id']  # so even same track id stranger will be "classified" (tracked) + for notifications - there track id is the best "classification"
                print(f"Person recognized: {person['name'] if person else 'new stranger'}")
                # TODO self.add_task('send_notification', name=person['name'] if person else None, global_id=self.trac_id_to_global_id[track_id], distance=person['_distance'] if person else None, frame=cropped_frame)
                add_embedding_to_existing_plot(embedding_vector, cropped_frame)
                continue  # run mode - skip the rest of the logic and continue to the next detection in the frame

            elif person is None:  # new person, mode run-save or train
                image_path = os.path.join(self.resources_path, 'faces', f"{uuid.uuid4()}.jpeg")
                self.add_task('save_image', frame=cropped_frame, image_path=image_path)  # Add the frame to the queue for processing
                person = create_person(embedding=embedding_vector, image=image_path, timestamp=int(time.time()))
                print(f"New person added: {person['global_id']}")
                self.trac_id_to_global_id[track_id] = person['global_id']  # to later maintain on tracker pipeline element
                detection.add_object(hailo.HailoClassification(type='1', label=person['name'], confidence=0.3))  # default min confidence for new person 
                
            elif (  # existing person, mode run-save or train, and good picture: order of conditions exploit lazy evaluation spare time
                len(person['faces_json']) < self.max_faces_per_person                                                       and
                1 - person['_distance'] > person['classificaiton_confidence_threshold'] + self.embedding_distance_tolerance and
                time.time() - person['last_image_recieved_time'] > self.last_image_sent_threshold_time                     and
                self.get_detection_num_pixels(detection.get_bbox(), width, height) > self.min_face_pixels_tolerance         and 
                self.calculate_procrustes_distance(detection, width, height) < self.procrustes_distance_threshold           and
                self.measure_blurriness(cropped_frame) > self.blurriness_tolerance  # takes ~0.01 seconds, for now skipping with return 400 always
            ):  
                print(f"Adding face to: {person['name']}/{person['global_id']}")
                image_path = os.path.join(self.resources_path, 'faces', f"{uuid.uuid4()}.jpeg")
                self.add_task('save_image', frame=cropped_frame, image_path=image_path)  # Add the frame to the queue for processing
                insert_new_face(person=person, embedding=embedding_vector, image=image_path, timestamp=int(time.time())) 
                self.trac_id_to_global_id[track_id] = person['global_id']  # to later maintain on tracker pipeline element
                detection.add_object(hailo.HailoClassification(type='1', label=person['name'], confidence=(1 - person['_distance']))) 
            
            else:  # existing regular
                self.trac_id_to_global_id[track_id] = person['global_id']
                try:
                    detection.add_object(hailo.HailoClassification(type='1', label=person['name'], confidence=(1 - person['_distance'])))
                except Exception as e:
                    breakpoint()
                    print(f"Error adding classification to detection: {e}")
        return Gst.PadProbeReturn.OK
    
    def train_vector_db_callback(self, pad, info, user_data):
        if self.current_file in self.processed_files:
            return Gst.PadProbeReturn.OK
        buffer = info.get_buffer()
        if buffer is None:
            return Gst.PadProbeReturn.OK
        format, width, height = get_caps_from_pad(pad)
        frame = get_numpy_from_buffer(buffer, format, width, height)
        roi = hailo.get_roi_from_buffer(buffer)
        for detection in (d for d in roi.get_objects_typed(hailo.HAILO_DETECTION) if d.get_label() == "face"):
            embedding = detection.get_objects_typed(hailo.HAILO_MATRIX)
            if len(embedding) != 1:  # we will continue if new embedding exists - might be new person, or another image of existing person
                continue  # if cropper pipeline element decided to pass the detection - it will arrive to this stage of the pipeline without face embedding. # print(f"Error: Expected 1 embedding, got {len(embedding)}")
            detection.remove_object(embedding[0])  # in case the detection pointer tracker pipeline element (from earlier side of the pipeline) holds is the same as the one we have, remove the embedding, so embedding similarity won't be part of the decision criteria
            cropped_frame = self.crop_frame(frame, detection.get_bbox(), width, height)
            embedding_vector = np.array(embedding[0].get_data())
            image_path = os.path.join(self.resources_path, 'faces', f"{uuid.uuid4()}.jpeg")
            self.add_task('save_image', frame=cropped_frame, image_path=image_path)  # Add the frame to the queue for processing
            name = os.path.basename(os.path.dirname(self.current_file))
            if self.is_name_processed(name):
                insert_new_face(person=get_person_by_id(self.get_processed_names_by_name(name)), embedding=embedding_vector, image=image_path, timestamp=int(time.time())) 
                print(f"Adding face to: {name}")
            else: 
                person = create_person(embedding=embedding_vector, image=image_path, timestamp=int(time.time()), name=name)
                print(f"New person added: {person['global_id']}")
                self.processed_names.add((name, person['global_id']))
            self.processed_files.add(self.current_file)
            return Gst.PadProbeReturn.OK  # in case of training - iterate exactly once per image
        return Gst.PadProbeReturn.OK
