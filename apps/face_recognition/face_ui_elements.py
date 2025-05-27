# region imports
# Standard library imports
from pathlib import Path

# Local application-specific imports
from hailo_apps_infra.hailo_core.hailo_common.base_ui_elements import BaseUIElements
from hailo_apps_infra.hailo_core.hailo_common.core import get_resource_path
from hailo_apps_infra.hailo_core.hailo_common.defines import RESOURCES_PHOTOS_DIR_NAME, HAILO_LOGO_PHOTO_NAME

# Third-party imports
from fastrtc import WebRTC
import gradio as gr
# endregion imports

class UIElements(BaseUIElements):
    """
    A class to hold references to all Gradio UI components.
    """
    def __init__(self):
        super().__init__()
        # Buttons
        self.start_btn = gr.Button("Start", variant="primary", elem_id="start-btn")
        self.stop_btn = gr.Button("Stop", variant="primary", elem_id="stop-btn")
        # Video Stream
        self.live_video_stream = WebRTC(modality="video", mode="receive", height="480px")

        # Embeddings
        self.embeddings_stream = gr.Plot(label="Embeddings Plot")

        # Sliders
        self.embedding_distance_tolerance = gr.Slider(
            minimum=0.0, maximum=1.0, value=0.1, label="Embedding Distance Tolerance", elem_id="embedding-distance-slider"
        )
        self.min_face_pixels_tolerance = gr.Slider(
            minimum=10000, maximum=100000, value=60000, label="Min Face Pixels Tolerance", elem_id="min-face-pixels-slider"
        )
        self.blurriness_tolerance = gr.Slider(
            minimum=0, maximum=1000, value=300, label="Blurriness Tolerance", elem_id="blurriness-slider"
        )
        self.max_faces_per_person = gr.Slider(
            minimum=1, maximum=10, value=3, label="Max Faces Per Person", elem_id="max-faces-slider"
        )
        self.last_image_sent_threshold_time = gr.Slider(
            minimum=0, maximum=10, value=1, label="Last Image Sent Threshold Time", elem_id="last-image-slider"
        )
        self.procrustes_distance_threshold = gr.Slider(
            minimum=0.0, maximum=1.0, value=0.3, label="Procrustes Distance Threshold", elem_id="procrustes-distance-slider"
        )
        # Text Areas
        self.ui_text_message = gr.TextArea(label="Detected Persons", interactive=False, elem_id="detected-persons-textarea")  # ID for custom styling

        # css
        self.ui_css = """
        .center-text { 
            text-align: center; 
        } 
        .fixed-size { 
            width: 480px; 
            height: 360px; 
        } 
        /* Ensure consistent size for video and embeddings */ 
        .equal-size { 
            width: 100%; 
        } 
        .same-height { 
            height: 360px;  /* Set a consistent height for sliders and detected persons */ 
        } 
        .limited-height {
            max-height: 600px;  /* Set a maximum height */
            outline: none;  /* Remove the orange focus outline */
            box-shadow: none;  /* Remove any focus-related shadow */
        }
        /* Enable scrolling for the detected persons TextArea */
        #detected-persons-textarea textarea {
            overflow-y: scroll;  /* Enable vertical scrolling */
            max-height: 80px; /* Match the height of the sliders */
            outline: none;  /* Remove the orange focus outline */
            box-shadow: none;  /* Remove any focus-related shadow */
        }
        .generating {
            border: none;
        }
        """

    def create_interface(self, ui_callbacks, pipeline):
        custom_theme = CustomTheme().set(
            loader_color="rgb(73, 175, 219)", 
            slider_color="rgb(73, 175, 219)")
        # UI elements to callbacks connection happens here because event listeners must be declared within gr.Blocks context
        with gr.Blocks(css=self.ui_css, theme=custom_theme) as interface:
            # region rendering
            with gr.Row():
                gr.Markdown("## Live Video Stream, Embeddings Visualization & Parameters tuning", elem_classes=["center-text"])
            # Row for buttons
            with gr.Row():
                self.start_btn.render()
                self.stop_btn.render()
                
            # Row for live video stream and embeddings_stream
            with gr.Row():
                with gr.Column(elem_classes=["fixed-size"]):  # Apply fixed size for live_video_stream
                    self.live_video_stream.render()
                with gr.Column(elem_classes=["fixed-size"]):  # Apply fixed size for embeddings_stream
                    self.embeddings_stream.render()
            
            # Row for sliders and detected persons
            with gr.Row():
                with gr.Column():
                    with gr.Row():
                        with gr.Column():
                            self.embedding_distance_tolerance.render()
                            self.min_face_pixels_tolerance.render()
                            self.blurriness_tolerance.render()
                        with gr.Column():
                            self.max_faces_per_person.render()
                            self.last_image_sent_threshold_time.render()
                            self.procrustes_distance_threshold.render()
                with gr.Column(elem_classes=["limited-height"]):  # Apply same-height class
                    self.ui_text_message.render()
            
            # Add the logo just above the footer
            # Define the original file and the alias (symlink) paths
            original_file = get_resource_path(pipeline_name=None, resource_type=RESOURCES_PHOTOS_DIR_NAME, model=HAILO_LOGO_PHOTO_NAME) 
            alias_file = Path(Path(__file__).parent, HAILO_LOGO_PHOTO_NAME)
            if not (alias_file.exists() or alias_file.is_symlink()):
                alias_file.symlink_to(original_file)
            with gr.Row():
                gr.HTML(
                    f"""
                        <img src=/gradio_api/file={Path(Path(__file__).parent, HAILO_LOGO_PHOTO_NAME)} style="display: block; margin: 0 auto; max-width: 300px;">
                    """
                )
            # endregion rendrering

            # region Event handlers: must be declared within gr.Blocks context
            self.live_video_stream.stream(  
                fn=ui_callbacks.process_frames,
                outputs=self.live_video_stream,
                trigger=self.start_btn.click
            )

            self.start_btn.click(
                fn=ui_callbacks.process_ui_text_message,
                inputs=None,
                outputs=self.ui_text_message
            )

            self.stop_btn.click(
                fn=ui_callbacks.stop_processing,
                inputs=None,
                outputs=None
            )

            if pipeline.options_menu.visualize:
                interface.load(
                    fn=ui_callbacks.consume_plot_queue,
                    inputs=None,
                    outputs=self.embeddings_stream
                )

            # Dynamically adjust initial values for sliders from pipeline
            self.embedding_distance_tolerance.value = pipeline.embedding_distance_tolerance 
            self.min_face_pixels_tolerance.value = pipeline.min_face_pixels_tolerance
            self.blurriness_tolerance.value = pipeline.blurriness_tolerance
            self.max_faces_per_person.value = pipeline.max_faces_per_person
            self.last_image_sent_threshold_time.value = pipeline.last_image_sent_threshold_time
            self.procrustes_distance_threshold.value = pipeline.procrustes_distance_threshold

            self.embedding_distance_tolerance.change(ui_callbacks.on_embedding_distance_change, inputs=self.embedding_distance_tolerance)
            self.min_face_pixels_tolerance.change(ui_callbacks.on_min_face_pixels_change, inputs=self.min_face_pixels_tolerance)
            self.blurriness_tolerance.change(ui_callbacks.on_blurriness_change, inputs=self.blurriness_tolerance)
            self.max_faces_per_person.change(ui_callbacks.on_max_faces_change, inputs=self.max_faces_per_person)
            self.last_image_sent_threshold_time.change(ui_callbacks.on_last_image_time_change, inputs=self.last_image_sent_threshold_time)
            self.procrustes_distance_threshold.change(ui_callbacks.on_procrustes_distance_change, inputs=self.procrustes_distance_threshold)
            # endregion event handlers

        return interface

# Define a custom theme
class CustomTheme(gr.themes.Default):
    def __init__(self):
        super().__init__()
        # Set the primary and secondary hues for the theme
        self.primary_hue = "rgb(66, 117, 233)"
        self.secondary_hue = "rgb(73, 175, 219)"
        
        # Set the font for all text
        self.font = "'Montserrat', sans-serif"
        
        # Customize button styles
        self.button_primary_background_fill = "linear-gradient(90deg, rgb(66, 117, 233) 0%, rgb(73, 175, 219) 100%)"
        self.button_primary_text_color = "white"
        self.button_primary_border_color = "transparent"
        self.button_primary_border_radius = "5px"

        # Add hover styles for buttons
        self.button_primary_background_fill_hover = "linear-gradient(90deg, rgb(73, 175, 219) 0%, rgb(66, 117, 233) 100%)"
        self.button_primary_text_color_hover = "white"