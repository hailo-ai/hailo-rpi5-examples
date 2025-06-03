# region imports
# Standard library imports
import time
import threading
import multiprocessing
from multiprocessing import Value
import queue
import signal
import json

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
PROCESS_UI_TEXT_MESSAGE_INTERVAL = 2
PROCESSING_STARTED_MESSAGE = "Processing started."
PROCESSING_STOPPED_MESSAGE = "Processing stopped."

# Database Configuration
DB_NAME = 'persons.db'
DB_TABLE_NAME = 'persons'
DB_SCHEMA = Record

# Visualization Process
VISUALIZATION_SLEEP_INTERVAL = 0.1  # Sleep interval for visualization loop
EMBEDDING_QUEUE_TIMEOUT = 0.1  # Timeout for embedding queue operations

# Pipeline States
PIPELINE_PLAYING_STATE = Gst.State.PLAYING
PIPELINE_PAUSED_STATE = Gst.State.PAUSED

# Thread Configuration
THREAD_DAEMON = False  # Daemon flag for threads
# endregion constants

class UICallbacks(BaseUICallbacks):
    is_started = Value('b', False)  # Shared boolean value across all instances
    plot_queue = multiprocessing.Queue()  # used only if self.pipeline.options_menu.visualize, create a queue to store plot_fig objects
    is_first_start = True  # Flag to indicate if this is the first start of the pipeline

    def __init__(self, pipeline):
        super().__init__(pipeline)
        self.latest_plot_image = None
        self.db_handler = DatabaseHandler(db_name=DB_NAME, table_name=DB_TABLE_NAME, schema=DB_SCHEMA)
        if self.pipeline.options_menu.visualize:
            self.start_visualization_process()

    def start_visualization_process(self):
        """Start the visualization process in a separate process."""
        db_records = self.db_handler.get_all_records()  # Get a copy of the records to avoid shared memory issues
        p = multiprocessing.Process(target=self.display_visualization_process, args=(db_records, self.pipeline.embedding_queue, self.pipeline.pipeline))
        p.daemon = THREAD_DAEMON  # Process will terminate when the main program exits
        p.start()
        self.pipeline.visualization_process = p 

    @staticmethod
    def display_visualization_process(db_records, embedding_queue, pipeline):
        """Run visualization in a separate process and yield embeddings."""
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # Ignore SIGINT in child processes
        while True:
            if UICallbacks.is_started.value:  # Check if processing has started
                visualizer = DatabaseVisualizer()  # Create a new visualizer in this process
                visualizer.set_db_records(db_records)
                UICallbacks.plot_queue.put(visualizer.visualize(mode='ui'))  # Initialize the plot for UI mode & Enqueue the plot
                break  # Exit after one iteration
            else:
                time.sleep(VISUALIZATION_SLEEP_INTERVAL)  # Add a small pause to prevent high CPU usage
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
                        timeout=EMBEDDING_QUEUE_TIMEOUT
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
                    time.sleep(VISUALIZATION_SLEEP_INTERVAL)  # when there are too many plot_figs in the queue, wait a bit before consuming more
            except queue.Empty:  # No plot_fig available in the queue
                time.sleep(VISUALIZATION_SLEEP_INTERVAL)  # Add a small pause to prevent high CPU usage
            except Exception as e:
                print(f"Error in consume_plot_queue: {e}")
                time.sleep(VISUALIZATION_SLEEP_INTERVAL)  # Add a small pause to prevent high CPU usage

    def process_ui_text_message(self):
        self.start_processing()  # Start processing, because this responds to start button click
        while not self.stop_event.is_set():
            yield "\n".join(self.pipeline.user_data.ui_text_message)  # Format the list as a string. self.pipeline.user_data.ui_text_message updated continuously in the pipeline via appcallback regardless of stop_event status
            time.sleep(PROCESS_UI_TEXT_MESSAGE_INTERVAL)

    def start_processing(self):
        """
        Function to start processing by clearing the stop_event flag.
        """
        if UICallbacks.is_first_start:  # Check if this is the first start
            app_thread = threading.Thread(target=self.pipeline.run, daemon=THREAD_DAEMON)
            app_thread.start()
            UICallbacks.is_first_start = False  # Set the flag to indicate that processing has started
        elif self.pipeline.pipeline.get_state(0)[1] != PIPELINE_PLAYING_STATE:
            self.pipeline.pipeline.set_state(PIPELINE_PLAYING_STATE)
        self.stop_event.clear()  # Unset the stop_event
        UICallbacks.is_started.value = True  # Set the flag to indicate processing has started
        print(PROCESSING_STARTED_MESSAGE)

    def stop_processing(self):
        """
        Function to stop processing by setting the stop_event flag.
        """
        self.pipeline.pipeline.send_event(Gst.Event.new_flush_start())  # Flush buffers
        self.pipeline.pipeline.set_state(PIPELINE_PAUSED_STATE)  # Set pipeline to PAUSED
        self.pipeline.pipeline.send_event(Gst.Event.new_flush_stop(False))  # Stop flushing
        self.stop_event.set()
        UICallbacks.is_started.value = False  # Reset the flag
        print(PROCESSING_STOPPED_MESSAGE)

    def on_min_face_pixels_change(self, value):
        self.pipeline.min_face_pixels_tolerance = value
        self.pipeline.algo_params['min_face_pixels_tolerance'] = value

    def on_blurriness_change(self, value):
        self.pipeline.blurriness_tolerance = value
        self.pipeline.algo_params['blurriness_tolerance'] = value

    def on_procrustes_distance_change(self, value):
        self.pipeline.procrustes_distance_threshold = value
        self.pipeline.algo_params['procrustes_distance_threshold'] = value

    def on_skip_frames_change(self, value):
        self.pipeline.skip_frames = value
        self.pipeline.algo_params['skip_frames'] = value

    def save_algo_params(self):
        """
        Save the algorithm parameters to the JSON file.
        """
        try:
            self.pipeline.json_file.seek(0)  # Move the file pointer to the beginning of the file
            json.dump(self.pipeline.algo_params, self.pipeline.json_file, indent=4)  # Write the updated JSON content back to the file
            self.pipeline.json_file.truncate()  # Truncate the file to remove any leftover content
        except Exception as e:
            print(f"Failed to save algo_params: {e}")
        finally:
            self.pipeline.json_file.close()  # Close the file