import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from io import BytesIO
from datetime import datetime, timedelta
from PIL import Image
import hailo
from hailo_apps_infra.hailo_rpi_common import app_callback_class
from face_recognition_pipeline_db import GStreamerFaceRecognitionApp
from db_handler import clear_table, init_database as db_init
import telebot

TELEGRAM_TOKEN = '7544346062:AAFSvYjJlvlby-rmJoUF3sWoXQh-7dxj2RY'
TELEGRAM_CHAT_ID = '7520285462'

class user_callbacks_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.ids_msg_sent = {}  # Dictionary to store the last sent time for each person
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            self.bot = telebot.TeleBot(TELEGRAM_TOKEN)
            self.chat_id = TELEGRAM_CHAT_ID

    def send_notification(self, name, global_id, distance, frame):
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            return
        caption = None  # Initialize caption with a default value
        current_time = datetime.now()
        last_sent_time = self.ids_msg_sent.get(global_id)
        if last_sent_time is None or current_time - last_sent_time > timedelta(hours=1):  # Check if the notification was sent more than an hour ago or never sent
            if not name:
                caption = "🚨 Unknown person detected!"  # For Unknown person there is no classification hence no classification confidence
            else:
                if name == 'Unknown':
                    caption = f"Detected {global_id} (confidence: {(1 - distance):.2f})"
                else:
                    caption = f"Detected {name} (confidence: {(1 - distance):.2f})"
        if caption:
            self.ids_msg_sent[global_id] = current_time  # Update the last sent time
            image = Image.fromarray(frame)  # Open the image from the file path
            image_byte_array = BytesIO()  # Save the image to a byte stream
            image.save(image_byte_array, format='PNG')
            image_byte_array.seek(0)
            try:
                self.bot.send_photo(self.chat_id, image_byte_array, caption)
            except Exception as e:
                print(f'Error sending Telegram notification: {str(e)}')

def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK
    user_data.increment()
    string_to_print = f'Frame count: {user_data.get_count()}\n'
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    for detection in detections:
        label = detection.get_label()
        detection_confidence = detection.get_confidence()
        if label == "face":
            track_id = 0
            track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
            if len(track) > 0:
                track_id = track[0].get_id()
            string_to_print += f'Detection track ID: {track_id} (Confidence: {detection_confidence:.1f})\n'
            classifications = detection.get_objects_typed(hailo.HAILO_CLASSIFICATION)
            if len(classifications) > 0:
                for classification in classifications:
                    string_to_print += f'Classification: {classification.get_label()} (Confidence: {classification.get_confidence():.1f})'
    # print(string_to_print)
    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    user_data = user_callbacks_class()
    app = GStreamerFaceRecognitionApp(app_callback, user_data)
    if app.options_menu.mode == 'delete':
        db, tbl_persons = db_init()
        clear_table()
        print("All records deleted from the database")
    else:  # run, run-save, train
        app.run()
