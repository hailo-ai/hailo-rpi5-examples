import os
import time
import numpy as np
import threading
import queue
import gradio as gr
import gi
import signal
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Import from existing project
from face_recognition_pipeline_db import GStreamerFaceRecognitionApp
from app_db import user_callbacks_class
import hailo  # Direct import instead of from hailo_platform
from hailo_apps_infra.hailo_rpi_common import get_numpy_from_buffer, get_caps_from_pad

# Initialize GStreamer
Gst.init(None)

class FaceRecognitionApp:
    def __init__(self):
        self.user_data = user_callbacks_class()
        self.app = None
        self.running = False
        self.recognition_history = queue.Queue(maxsize=100)  # Store live recognition history
        self.last_frame = np.zeros((480, 640, 3), dtype=np.uint8)  # Default black frame
        self.pipeline_thread = None

    def start_pipeline(self):
        """Start the GStreamer pipeline."""
        if self.running:
            return "Pipeline is already running."
        
        self.app = GStreamerFaceRecognitionApp(self.frame_callback, self.user_data)
        self.running = True
        self.pipeline_thread = threading.Thread(target=self.app.run)
        self.pipeline_thread.daemon = True
        self.pipeline_thread.start()
        return "Pipeline started."

    def stop_pipeline(self):
        """Stop the GStreamer pipeline."""
        if not self.running:
            return "Pipeline is not running."
        
        self.running = False
        if self.app and self.app.pipeline:
            self.app.pipeline.set_state(Gst.State.NULL)
        if self.pipeline_thread:
            self.pipeline_thread.join(timeout=2)
        self.app = None
        return "Pipeline stopped."

    def frame_callback(self, pad, info, user_data):
        """Callback to process frames and update recognition history."""
        buffer = info.get_buffer()
        if buffer is None:
            return Gst.PadProbeReturn.OK
        
        try:
            # Extract frame and recognition data
            format, width, height = get_caps_from_pad(pad)
            frame = get_numpy_from_buffer(buffer, format, width, height)
            self.last_frame = frame.copy()

            roi = hailo.get_roi_from_buffer(buffer)
            detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
            for detection in detections:
                if detection.get_label() == "face":
                    classifications = detection.get_objects_typed(hailo.HAILO_CLASSIFICATION)
                    if classifications:
                        for classification in classifications:
                            name = classification.get_label()
                            confidence = classification.get_confidence()
                            self.update_recognition_history(name, confidence)
        except Exception as e:
            print(f"Error in frame callback: {e}")
        
        return Gst.PadProbeReturn.OK

    def update_recognition_history(self, name, confidence):
        """Update the live recognition history."""
        if self.recognition_history.full():
            self.recognition_history.get()  # Remove the oldest entry
        self.recognition_history.put(f"{name} (Confidence: {confidence:.2f})")

    def get_recognition_history(self):
        """Retrieve the live recognition history."""
        return "\n".join(list(self.recognition_history.queue))

    def get_current_frame(self):
        """Retrieve the latest frame."""
        return self.last_frame

def create_interface():
    app = FaceRecognitionApp()

    with gr.Blocks(title="Hailo Face Recognition") as interface:
        gr.Markdown("# Hailo Face Recognition System")
        status = gr.Textbox(label="Status", interactive=False)
        
        with gr.Tab("Live Recognition"):
            with gr.Row():
                video_output = gr.Image(label="Recognition Output", interactive=False)
                recognized_faces = gr.TextArea(label="Live Recognized Persons", interactive=False, lines=15)
            
            with gr.Row():
                start_btn = gr.Button("Start Recognition")
                stop_btn = gr.Button("Stop Recognition")
                refresh_video_btn = gr.Button("Refresh Video")
                refresh_faces_btn = gr.Button("Refresh Recognized Persons")
        
        # Event handlers
        start_btn.click(
            fn=app.start_pipeline,
            inputs=[],
            outputs=[status]
        )
        
        stop_btn.click(
            fn=app.stop_pipeline,
            inputs=[],
            outputs=[status]
        )
        
        refresh_video_btn.click(
            fn=app.get_current_frame,
            inputs=[],
            outputs=[video_output]
        )

        refresh_faces_btn.click(
            fn=app.get_recognition_history,
            inputs=[],
            outputs=[recognized_faces]
        )
        
        # Add JavaScript for auto-refresh
        gr.HTML("""
        <script>
        function autoRefresh() {
            document.querySelector('button:contains("Refresh Video")').click();
            document.querySelector('button:contains("Refresh Recognized Persons")').click();
            setTimeout(autoRefresh, 100);  // Refresh every 100ms
        }
        setTimeout(autoRefresh, 1000);  // Start refreshing after 1 second
        </script>
        """)
    
    return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_name="0.0.0.0")