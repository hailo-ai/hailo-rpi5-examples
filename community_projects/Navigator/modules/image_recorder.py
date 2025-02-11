import threading
import time
import os
import cv2
from datetime import datetime   
class ImageRecorder(threading.Thread):
    def __init__(self, frame_grabber, storage_dir):
        """
        Initialize the ImageRecorder class.

        Args:
            frame_grabber (FrameGrabber): Instance of an existing FrameGrabber.
            storage_dir (str): Directory to store recorded images.
        """
        super().__init__()
        self.frame_grabber = frame_grabber
        self.storage_dir = storage_dir
        self.running = False
        self.mode = "playback"  # Modes: 'record' or 'playback'
        self.output_queue = []
        self.current_image_index = 0

        # Ensure the storage directory exists
        os.makedirs(storage_dir, exist_ok=True)

    def run(self):
        self.running = True
        while self.running:
            if self.mode == "record":
                self.record_images()
            elif self.mode == "playback":
                time.sleep(0.1)  # Sleep to avoid busy looping in playback mode

    def stop(self):
        """
        Stop the thread and release resources.
        """
        self.running = False

    def switch_to_record(self):
        """
        Switch to recording mode.
        """
        self.mode = "record"

    def switch_to_playback(self):
        """
        Switch to playback mode and reset the playback index.
        """
        self.mode = "playback"
        self.current_image_index = 0

    def record_images(self):
        """
        Continuously capture and save images every 0.5 seconds in sequential order using the frame grabber.
        """
        while self.mode == "record" and self.running:
            frame = self.frame_grabber.get_last_frame()

            if frame is not None:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S%f")
                filename = os.path.join(self.storage_dir, f"image_{timestamp}.png")
                cv2.imwrite(filename, frame)
                print(f"Image saved: {filename}")
                time.sleep(0.3)
            else:
                print("No frame available from frame grabber.")

    def get_next_image(self):
        """
        Get the next image in playback mode.

        Returns:
            frame (numpy array): The next image frame, or None if no more images are available.
        """
        if self.mode == "playback":
            image_files = sorted(os.listdir(self.storage_dir))
            print(len(image_files),"images found")
            if self.current_image_index < len(image_files):
                image_file = image_files[self.current_image_index]
                image_path = os.path.join(self.storage_dir, image_file)
                frame = cv2.imread(image_path)
                if frame is not None:
                    self.current_image_index += 1
                    print(f"Sent image: {image_path}")
                    return frame
                else:
                    print(f"Failed to load image: {image_path}")
            else:
                print("No more images to display.")
        return None

    def get_previous_image(self):
        """
        Get the previous image in playback mode.

        Returns:
            frame (numpy array): The previous image frame, or None if no more images are available.
        """
        if self.mode == "playback":
            image_files = sorted(os.listdir(self.storage_dir))
            if self.current_image_index > 0:
                self.current_image_index -= 1
                image_file = image_files[self.current_image_index]
                image_path = os.path.join(self.storage_dir, image_file)
                frame = cv2.imread(image_path)
                if frame is not None:
                    print(f"Sent image: {image_file}")
                    return frame
                else:
                    print(f"Failed to load image: {image_path}")
            else:
                print("Already at the first image.")
        return None

    def clean_images(self):
        """
        Remove all images from the storage directory.
        """
        image_files = os.listdir(self.storage_dir)
        for image_file in image_files:
            file_path = os.path.join(self.storage_dir, image_file)
            try:
                os.remove(file_path)
                print(f"Deleted image: {file_path}")
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")

