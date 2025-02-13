import cv2
import numpy as np
import threading
from time import time, sleep


class FrameGrabber(threading.Thread):
    def __init__(self, cap, width, height):
        super().__init__()
        self.cap = cap
        _, self.frame = self.cap.read()
        self.running = False
        self.width = width
        self.height = height
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30
        self.fourcc = cv2.VideoWriter_fourcc(*"X264")
        self.hls_directory = "./test"
        # self.gst_hls_pipeline = (
        #     f"appsrc ! "
        #     f"videoconvert ! "
        #     f"x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! "
        #     f"mpegtsmux ! "
        #     f"hlssink location={self.hls_directory}/segment_%05d.ts playlist-location={self.hls_directory}/playlist.m3u8 target-duration=5 max-files=5"
        # )

    def run(self):
        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("Can't receive frame (stream ended?).")
            if (frame is None) or (self.frame is None):
                print("BADDDDD")
    
            self.frame = frame
            sleep(0.05)

    def stop(self):
        self.running = False
        self.cap.release()

    def get_last_frame(self):
        self.frame = np.resize(self.frame, (self.height, self.width, 3))
        return self.frame

