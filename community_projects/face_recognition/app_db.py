import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
from io import BytesIO
from datetime import datetime, timedelta
from PIL import Image
import hailo
from hailo_apps_infra.hailo_rpi_common import app_callback_class
from face_recognition_pipeline_db import GStreamerFaceRecognitionApp
from db_handler import get_all_persons, clear_table, remove_face_by_id, update_person_name, init_database as db_init
import telebot
import matplotlib.pyplot as plt

TELEGRAM_TOKEN = ''  # TODO
TELEGRAM_CHAT_ID = ''  # TODO

class user_callbacks_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.ids_msg_sent = {}  # Dictionary to store the last sent time for each person
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            self.bot = telebot.TeleBot(TELEGRAM_TOKEN)
            self.chat_id = TELEGRAM_CHAT_ID

    def send_notification(self, person, frame):
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            return
        current_time = datetime.now()
        last_sent_time = self.ids_msg_sent.get(person['global_id'])

        # Check if the notification was sent more than an hour ago or never sent
        if last_sent_time is None or current_time - last_sent_time > timedelta(hours=1):
            if person['name'] != 'Unknown':
                caption = f"{person['name']} detected (confidence: {int(1 - person['_distance'])})"
            else:
                caption = "🚨 Unknown person detected!"  # For Unknown person there is no classification hence no classification confidence

            self.ids_msg_sent[person['global_id']] = current_time  # Update the last sent time
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

def show_image_non_blocking(image, title):
    plt.figure()
    plt.imshow(image)
    plt.title(title)
    plt.show(block=False)
    plt.pause(0.001)  # Add a small pause to allow the image to render

def update_persons():
    for person in get_all_persons(only_unknowns=True):
        print(f"Updating person: {person['global_id']}" + (f" - {person['name']}" if person['name'] != 'Unknown' else ""))
        first_name = None
        for face in person['faces_json']:
            image = Image.open(face['image'])
            show_image_non_blocking(image, f"Person ID: {person['global_id']}")
            action = input("Enter the name of the person or 'delete' to remove this image: ").strip()
            plt.close()  # Close the image after input is submitted
            if action.lower() == 'delete':
                if not remove_face_by_id(person, face['id']):
                    print(f"Image {face['id']} deleted.")
                else:
                    print(f"This was the last image of this person - person removed from DB.")
            else:
                if first_name is None:
                    first_name = action
                    update_person_name(person['global_id'], action)
                    print(f"Person name updated to {action}.")
                else:
                    if action != first_name:
                        print(f"Conflicting names: '{first_name}' and '{action}'")
                        selected_name = input(f"Select the correct name ('{first_name}' or '{action}'): ").strip()
                        while selected_name not in [first_name, action]:
                            selected_name = input(f"Invalid selection. Please select '{first_name}' or '{action}': ").strip()
                        first_name = selected_name
                        update_person_name(person['global_id'], selected_name)
                        print(f"Person name updated to {selected_name}.")
        print('Finished updating.')

if __name__ == "__main__":
    user_data = user_callbacks_class()
    app = GStreamerFaceRecognitionApp(app_callback, user_data)
    if app.options_menu.mode == 'delete':
        db, tbl_persons = db_init()
        clear_table()
        print("All records deleted from the database")
    elif app.options_menu.mode == 'update':
        update_persons()  # use the web interface instead
    else:  # run, run-save, train
        app.run()
