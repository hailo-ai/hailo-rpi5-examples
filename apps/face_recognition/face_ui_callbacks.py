# region imports
# Standard library imports
import time
import threading
import multiprocessing
from multiprocessing import Value
import queue
import time

# Third-party imports
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
        
# Local application-specific imports
from hailo_apps_infra.hailo_core.hailo_common.base_ui_callbacks import BaseUICallbacks
from hailo_apps_infra.hailo_core.hailo_common.db_handler import DatabaseHandler, Record
from hailo_apps_infra.hailo_core.hailo_common.db_visualizer import DatabaseVisualizer
# endregion imports

# region constants
EMBEDDING_TIMEOUT = 0.5
RESULT_QUEUE_TIMEOUT = 2
WORKER_SLEEP_INTERVAL = 3 
PROCESS_DETECTED_PERSONS_INTERVAL = 2
PROCESSING_STARTED_MESSAGE = "Processing started."
PROCESSING_STOPPED_MESSAGE = "Processing stopped."
# endregion constants

class UICallbacks(BaseUICallbacks):
    is_started = Value('b', False)  # Shared boolean value across all instances
    plot_queue = multiprocessing.Queue()  # used only if self.pipeline.options_menu.visualize, create a queue to store plot_fig objects
    is_first_start = True  # Flag to indicate if this is the first start of the pipeline

    def __init__(self, pipeline):
        super().__init__(pipeline)
        self.latest_plot_image = None
        self.db_handler = DatabaseHandler(db_name='persons.db', table_name='persons', schema=Record)
        if self.pipeline.options_menu.visualize:
            self.start_visualization_process()

    def start_visualization_process(self):
        """Start the visualization process in a separate process."""
        db_records = self.db_handler.get_all_records()  # Get a copy of the records to avoid shared memory issues
        p = multiprocessing.Process(target=self.display_visualization_process, args=(db_records, self.pipeline.embedding_queue, self.pipeline.pipeline))
        p.daemon = True  # Process will terminate when the main program exits
        p.start()
        self.visualization_process = p 

    @staticmethod
    def display_visualization_process(db_records, embedding_queue, pipeline):
        """Run visualization in a separate process and yield embeddings."""
        while True:
            if UICallbacks.is_started.value:  # Check if processing has started
                visualizer = DatabaseVisualizer()  # Create a new visualizer in this process
                visualizer.set_db_records(db_records)
                UICallbacks.plot_queue.put(visualizer.visualize(mode='ui'))  # Initialize the plot for UI mode & Enqueue the plot
                break  # Exit after one iteration
            else:
                time.sleep(0.1)  # Add a small pause to prevent high CPU usage
        while UICallbacks.is_started.value:  # Append the new embeddings to the plot
            try:
                embeddings = []
                labels = []

                # Retrieve all items from the queue
                while not embedding_queue.empty():
                    embedding_vector, label = embedding_queue.get_nowait()
                    embeddings.append(embedding_vector)
                    labels.append(label)

                if embeddings:  # Only update the plot if there are new embeddings
                    UICallbacks.plot_queue.put(
                        visualizer.add_embeddings_to_existing_plot(
                            embeddings=embeddings, labels=labels, mode='ui'
                        ),
                        timeout=0.1
                    )
                time.sleep(1)
            except queue.Empty:  # No embedding available in the queue
                time.sleep(1)  # Add a small pause to prevent high CPU usage
            except Exception as e:
                print(f"Error in visualization process: {e}")
                break

    def consume_plot_queue(self):
        """Consume plot_fig from the queue and process it."""
        while True:  # can't be self.stop_event.is_set() because not responding to start button click, rather page init (gradio interface load)
            try:
                if not self.stop_event.is_set():
                    yield UICallbacks.plot_queue.get_nowait()  # Get plot_fig from the queue
                    time.sleep(0.1)  # when there are too many plot_figs in the queue, wait a bit before consuming more
            except queue.Empty:  # No plot_fig available in the queue
                time.sleep(0.1)  # Add a small pause to prevent high CPU usage
            except Exception as e:
                print(f"Error in consume_plot_queue: {e}")
                time.sleep(0.1)  # Add a small pause to prevent high CPU usage

    def process_detected_persons(self):
        self.start_processing()  # Start processing, because this responds to start button click
        while not self.stop_event.is_set():
            yield "\n".join(self.pipeline.user_data.detected_persons)  # Format the list as a string. self.pipeline.user_data.detected_persons updated continuously in the pipeline via appcallback regardless of stop_event status
            time.sleep(PROCESS_DETECTED_PERSONS_INTERVAL)

    def start_processing(self):
        """
        Function to start processing by clearing the stop_event flag.
        """
        if UICallbacks.is_first_start:  # Check if this is the first start
            app_thread = threading.Thread(target=self.pipeline.run, daemon=False)
            app_thread.start()
            UICallbacks.is_first_start = False  # Set the flag to indicate that processing has started
        elif self.pipeline.pipeline.get_state(0)[1] != Gst.State.PLAYING:
            self.pipeline.pipeline.set_state(Gst.State.PLAYING)
        self.stop_event.clear()  # Unset the stop_event
        UICallbacks.is_started.value = True  # Set the flag to indicate processing has started
        print(PROCESSING_STARTED_MESSAGE)

    def stop_processing(self):
        """
        Function to stop processing by setting the stop_event flag.
        """
        self.pipeline.pipeline.send_event(Gst.Event.new_flush_start())  # Flush buffers
        self.pipeline.pipeline.set_state(Gst.State.PAUSED)  # Set pipeline to PAUSED
        self.pipeline.pipeline.send_event(Gst.Event.new_flush_stop(False))  # Stop flushing
        self.stop_event.set()
        UICallbacks.is_started.value = False  # Reset the flag
        print(PROCESSING_STOPPED_MESSAGE)

    def on_embedding_distance_change(self, value):
        self.pipeline.embedding_distance_tolerance = value

    def on_min_face_pixels_change(self, value):
        self.pipeline.min_face_pixels_tolerance = value

    def on_blurriness_change(self, value):
        self.pipeline.blurriness_tolerance = value

    def on_max_faces_change(self, value):
        self.pipeline.max_faces_per_person = value

    def on_last_image_time_change(self, value):
        self.pipeline.last_image_sent_threshold_time = value

    def on_procrustes_distance_change(self, value):
        self.pipeline.procrustes_distance_threshold = value
    
    def clear_queue_keep_last(self, queue):
        """Helper function to clear all items from a queue except the last one."""
        last_item = None
        while not queue.empty():
            try:
                last_item = queue.get_nowait()  # Remove an item from the queue without blocking
            except queue.Empty:
                break

        # If there was at least one item, re-add the last one to the queue
        if last_item is not None:
            queue.put(last_item)