import uuid
import wave
import subprocess

import queue
import subprocess
import os
import time

# Job queue to store WAV file paths
job_queue = queue.Queue()

WAV_DIR = "/tmp"

# Worker thread function that processes each file in the queue
def worker():
    while True:
        # Wait for a new job (file path) from the queue
        wav_file = job_queue.get()

        if wav_file is None:
            # If we get a 'None' value, it means we should stop the worker
            print("Worker exiting.")
            break

        print(f"Worker is playing: {wav_file}")

        # Play the WAV file using paplay
        play_wav(wav_file)

        # Indicate that the task is done
        job_queue.task_done()

# Producer thread function that waits for new WAV files and adds them to the queue
def play_streams():
    # Continuously check the directory for new WAV files
    processed_files = set()  # Track files already added to the queue

    while True:
        # Get a list of all WAV files in the directory
        wav_files = [f for f in os.listdir(WAV_DIR) if f.endswith(".wav")]
        
        # Add new files to the queue
        for file in wav_files:
            if file not in processed_files:
                file_path = os.path.join(WAV_DIR, file)
                print(f"Producer adding: {file_path}")
                job_queue.put(file_path)
                processed_files.add(file)

        time.sleep(1)  # Wait a bit before checking again (to simulate real-time)

def generate_wav(pcm_data, path=None, sample_rate=44100):
    if not path:
        path = os.path.join(WAV_DIR, str(uuid.uuid4())+".wav")
    with wave.open(path, 'w') as wav_file:
        wav_file.setnchannels(2)  # Stereo
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)  # Sample rate (44.1 kHz)
        wav_file.writeframes(pcm_data)
    return path

def play_wav(path):
    subprocess.run(["mplayer", "-ao", "pulse", path])
