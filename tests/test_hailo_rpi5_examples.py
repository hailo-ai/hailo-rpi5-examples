import pytest
import subprocess
import os
import sys
import time
import signal
import glob
from picamera2 import Picamera2

def get_device_architecture():
    """Get the device architecture from hailortcli."""
    try:
        result = subprocess.run(['hailortcli', 'fw-control', 'identify'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "Device Architecture" in line:
                return line.split(':')[1].strip()
    except Exception:
        return "unknown"

def get_available_cameras():
    """Get a list of available video devices."""
    video_devices = glob.glob('/dev/video*')
    cameras = []
    for device in video_devices:
        result = subprocess.run(['v4l2-ctl', '--device', device, '--all'], capture_output=True, text=True)
        if "bcm2835" in result.stdout:
            cameras.append(("rpi", device))
        elif "USB" in result.stdout:
            cameras.append(("usb", device))
    return cameras

def get_compatible_hefs(architecture):
    """Get a list of compatible HEF files based on the device architecture."""
    all_hefs = glob.glob('resources/*.hef')
    compatible_hefs = []
    for hef in all_hefs:
        hef_name = os.path.basename(hef)
        if any(keyword in hef_name.lower() for keyword in ['barcode', 'pose', 'seg']):
            continue
        if architecture == 'HAILO8L':
            if 'h8l' in hef_name.lower():
                compatible_hefs.append(hef)
        elif architecture == 'HAILO8':
            if 'h8l' not in hef_name.lower():
                compatible_hefs.append(hef)
        else:
            compatible_hefs.append(hef)
    return compatible_hefs

def test_combined_pipeline():
    """
    Combined test function for basic pipeline scripts with different HEFs and input sources.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    architecture = get_device_architecture()
    compatible_hefs = get_compatible_hefs(architecture)
    available_cameras = get_available_cameras()

    for hef in compatible_hefs:
        hef_name = os.path.basename(hef)
        
        # Test with video input
        log_file_path = os.path.join(log_dir, f"detection_{hef_name}_video_test.log")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(['python', 'basic_pipelines/detection.py', '--input', 'resources/detection0.mp4', '--hef-path', hef],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(30)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"Detection with {hef_name} (video input) could not be terminated within 5 seconds after running for 30 seconds")

            stdout, stderr = process.communicate()
            log_file.write(f"Detection with {hef_name} (video input) stdout:\n{stdout.decode()}\n")
            log_file.write(f"Detection with {hef_name} (video input) stderr:\n{stderr.decode()}\n")

            assert "Traceback" not in stderr.decode(), f"Detection with {hef_name} (video input) encountered an exception: {stderr.decode()}"
            assert "Error" not in stderr.decode(), f"Detection with {hef_name} (video input) encountered an error: {stderr.decode()}"
            assert "frame" in stdout.decode().lower(), f"Detection with {hef_name} (video input) did not process any frames"
            assert "detection" in stdout.decode().lower(), f"Detection with {hef_name} (video input) did not make any detections"

        # Test with available cameras
        for camera_type, device in available_cameras:
            log_file_path = os.path.join(log_dir, f"detection_{hef_name}_{camera_type}_camera_test.log")
            with open(log_file_path, "w") as log_file:
                process = subprocess.Popen(['python', 'basic_pipelines/detection.py', '--input', device, '--hef-path', hef],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    time.sleep(20)
                    process.send_signal(signal.SIGTERM)
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    pytest.fail(f"Detection with {hef_name} ({camera_type} camera) could not be terminated within 5 seconds after running for 20 seconds")

                stdout, stderr = process.communicate()
                log_file.write(f"Detection with {hef_name} ({camera_type} camera) stdout:\n{stdout.decode()}\n")
                log_file.write(f"Detection with {hef_name} ({camera_type} camera) stderr:\n{stderr.decode()}\n")

                assert "Traceback" not in stderr.decode(), f"Detection with {hef_name} ({camera_type} camera) encountered an exception: {stderr.decode()}"
                assert "Error" not in stderr.decode(), f"Detection with {hef_name} ({camera_type} camera) encountered an error: {stderr.decode()}"

    print("All tests completed successfully.")

if __name__ == "__main__":
    pytest.main(["-v", __file__])