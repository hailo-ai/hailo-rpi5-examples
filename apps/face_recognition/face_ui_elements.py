# region imports
# Standard library imports
from pathlib import Path

# Local application-specific imports
from hailo_apps_infra.hailo_core.hailo_common.base_ui_elements import BaseUIElements
from hailo_apps_infra.hailo_core.hailo_common.core import get_resource_path
from hailo_apps_infra.hailo_core.hailo_common.defines import DEFAULT_LOCAL_RESOURCES_PATH, HAILO_LOGO_PHOTO_NAME

# Third-party imports
from fastrtc import WebRTC
import gradio as gr
# endregion imports

# region Global Variables
# Slider configurations
CLASSIFICATION_THRESHOLD_MIN = 0.0
CLASSIFICATION_THRESHOLD_MAX = 1.0
SKIP_FRAMES_MIN = 0.0
SKIP_FRAMES_MAX = 60

# Theme colors
PRIMARY_HUE_COLOR = "rgb(66, 117, 233)"
SECONDARY_HUE_COLOR = "rgb(73, 175, 219)"
BUTTON_PRIMARY_TEXT_COLOR = "white"
BUTTON_PRIMARY_BORDER_COLOR = "transparent"
# endregion Global Variables

class UIElements(BaseUIElements):
    """
    A class to hold references to all Gradio UI components.
    """
    def __init__(self):
        super().__init__()
        # Buttons
        self.start_btn = gr.Button("Start", variant="primary", elem_id="start-btn")
        # Video Stream
        self.live_video_stream = WebRTC(modality="video", mode="receive", height="480px")

        # Embeddings
        self.embeddings_stream = gr.Plot(label="Embeddings Plot")

        # Sliders
        self.lance_db_vector_search_classificaiton_confidence_threshold = gr.Slider(
            minimum=CLASSIFICATION_THRESHOLD_MIN, maximum=CLASSIFICATION_THRESHOLD_MAX, label="Classificaiton confidence threshold", elem_id="classificaiton-confidence-threshold-slider"
        )
        self.skip_frames = gr.Slider(
            minimum=SKIP_FRAMES_MIN, maximum=SKIP_FRAMES_MAX, label="Frames to skip before trying to recognize", elem_id="skip-frames-slider"
        )
        # Text Areas
        self.ui_text_message = gr.TextArea(label="Detected Persons", interactive=False, elem_id="detected-persons-textarea")  # ID for custom styling

        self.save_btn = gr.Button("Save", variant="primary", elem_id="save-btn")

        # css
        self.ui_css = """
        .center-text { 
            text-align: center; 
        } 
        .fixed-size { 
            width: 480px; 
            height: 360px; 
        }  
        /* Enable scrolling for the detected persons TextArea */
        #detected-persons-textarea textarea {
            overflow-y: scroll;  /* Enable vertical scrolling */
            max-height: 97px; /* Match the height of the sliders */
            outline: none;  /* Remove the orange focus outline */
            box-shadow: none;  /* Remove any focus-related shadow */
        }
        .generating {
            border: none;
        }
        """

    def create_interface(self, ui_callbacks, pipeline):
        custom_theme = CustomTheme().set(
            loader_color=SECONDARY_HUE_COLOR, 
            slider_color=SECONDARY_HUE_COLOR)
        # UI elements to callbacks connection happens here because event listeners must be declared within gr.Blocks context
        with gr.Blocks(css=self.ui_css, theme=custom_theme) as interface:
            # region rendering
            with gr.Row():
                gr.Markdown("## Live Video Stream, Embeddings Visualization & Parameters tuning", elem_classes=["center-text"])
            # Row for buttons
            with gr.Row():
                with gr.Column(scale=1, min_width=300):
                    self.start_btn.render()
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
                            self.lance_db_vector_search_classificaiton_confidence_threshold.render()
                        with gr.Column():
                            self.skip_frames.render()
                    with gr.Row():
                        with gr.Column():
                            self.save_btn.render()
                with gr.Column():
                    self.ui_text_message.render()
            with gr.Row():
                # Add the logo just above the footer
                # Define the original file and the alias (symlink) paths
                original_file = get_resource_path(pipeline_name=None, resource_type=DEFAULT_LOCAL_RESOURCES_PATH, model=HAILO_LOGO_PHOTO_NAME) 
                alias_file = Path(Path(__file__).parent, HAILO_LOGO_PHOTO_NAME)
                if not (alias_file.exists() or alias_file.is_symlink()):
                    alias_file.symlink_to(original_file)
                with gr.Column():
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

            self.save_btn.click(
                fn=ui_callbacks.save_algo_params,
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
            self.lance_db_vector_search_classificaiton_confidence_threshold.value = pipeline.lance_db_vector_search_classificaiton_confidence_threshold
            self.skip_frames.value = pipeline.skip_frames

            self.lance_db_vector_search_classificaiton_confidence_threshold.change(ui_callbacks.on_lance_db_vector_search_classificaiton_confidence_threshold_change, inputs=self.lance_db_vector_search_classificaiton_confidence_threshold)
            self.skip_frames.change(ui_callbacks.on_skip_frames_change, inputs=self.skip_frames)
            # endregion event handlers

        return interface

# Define a custom theme
class CustomTheme(gr.themes.Default):
    def __init__(self):
        super().__init__()
        # Set the primary and secondary hues for the theme
        self.primary_hue = PRIMARY_HUE_COLOR
        self.secondary_hue = SECONDARY_HUE_COLOR
        
        # Set the font for all text
        self.font = "'Montserrat', sans-serif"
        
        # Customize button styles
        self.button_primary_background_fill = f"linear-gradient(90deg, {PRIMARY_HUE_COLOR} 0%, {SECONDARY_HUE_COLOR} 100%)"
        self.button_primary_text_color = BUTTON_PRIMARY_TEXT_COLOR
        self.button_primary_border_color = BUTTON_PRIMARY_BORDER_COLOR
        self.button_primary_border_radius = "5px"

        # Add hover styles for buttons
        self.button_primary_background_fill_hover = f"linear-gradient(90deg, {SECONDARY_HUE_COLOR} 0%, {PRIMARY_HUE_COLOR} 100%)"
        self.button_primary_text_color_hover = BUTTON_PRIMARY_TEXT_COLOR