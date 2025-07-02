import pytest
import subprocess
import os
import sys
import time
import signal
import glob
import logging
import re

from hailo_apps.hailo_app_python.core.common.camera_utils import get_usb_video_devices

try:
    from picamera2 import Picamera2
    rpi_camera_available = True
except ImportError:
    rpi_camera_available = False

TEST_RUN_TIME = 10

def test_rpi_camera_connection():
    """Test if RPI camera is connected by running rpicam-hello."""
    if not rpi_camera_available:
        pytest.skip("RPi camera is not available")
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "rpi_camera_test.log")

    with open(log_file_path, "w") as log_file:
        process = subprocess.Popen(
            ['rpicam-hello', '-t', '0', '--post-process-file', '/usr/share/rpi-camera-assets/hailo_yolov6_inference.json'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            time.sleep(TEST_RUN_TIME)
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail(f"RPI camera connection test could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")

        stdout, stderr = process.communicate()
        log_file.write(f"rpi_camera stdout:\n{stdout.decode()}\n")
        log_file.write(f"rpi_camera stderr:\n{stderr.decode()}\n")

        # Check for the specific error message
        if "ERROR: *** no cameras available ***" in stderr.decode():
            pytest.fail("RPI camera is not connected")
        else:
            log_file.write("RPI camera is connected and working.\n")
            log_file.write("Test completed successfully.\n")

def get_device_architecture():
    """Get the device architecture from hailortcli."""
    try:
        result = subprocess.run(['hailortcli', 'fw-control', 'identify'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "Device Architecture" in line:
                return line.split(':')[1].strip().lower()
    except Exception:
        return "unknown"

def get_pipelines_list():
    """Get a list of available pipeline scripts."""
    return ["detection.py", "detection_simple.py", "pose_estimation.py", "instance_segmentation.py", "depth.py"]

def get_detection_compatible_hefs(architecture):
    """Get a list of compatible HEF files based on the device architecture."""
    H8_HEFS = [
        "yolov5m_wo_spp.hef",
        "yolov6n.hef",
        "yolov8s.hef",
        "yolov8m.hef",
        "yolov11n.hef",
        "yolov11s.hef"
    ]

    H8L_HEFS = [
        "yolov5m_wo_spp.hef",
        "yolov6n.hef",
        "yolov8s.hef",
        "yolov8m.hef",
        "yolov11n.hef",
        "yolov11s.hef"
    ]
    hef_list = H8L_HEFS
    if architecture == 'hailo8':
        hef_list = H8_HEFS
        return [os.path.join("resources","models","hailo8", hef) for hef in hef_list]

    return [os.path.join("resources","models","hailo8l", hef) for hef in hef_list]


def get_pose_compatible_hefs(architecture):
    """Get a list of compatible HEF files based on the device architecture."""
    H8_HEFS = [
        "yolov8m_pose.hef",
        "yolov8s_pose.hef",
    ]

    H8L_HEFS = [
        "yolov8s_pose.hef",
    ]
    hef_list = H8L_HEFS
    if architecture == 'hailo8':
        # check both HAILO8 and HAILO8L
        hef_list = H8_HEFS
        return [os.path.join("resources","models","hailo8", hef) for hef in hef_list]

    return [os.path.join("resources","models","hailo8l", hef) for hef in hef_list]

def get_seg_compatible_hefs(architecture):
    """Get a list of compatible HEF files based on the device architecture."""
    H8_HEFS = [
        "yolov5m_seg.hef",
        "yolov5n_seg.hef",
    ]

    H8L_HEFS = [
        "yolov5n_seg.hef",
    ]
    hef_list = H8L_HEFS
    if architecture == 'hailo8':
        # check both HAILO8 and HAILO8L
        hef_list = H8_HEFS
        return [os.path.join("resources","models","hailo8", hef) for hef in hef_list]

    return [os.path.join("resources","models","hailo8l", hef) for hef in hef_list]

def get_depth_compatible_hefs(architecture):
    """Get a list of compatible HEF files based on the device architecture."""
    H8_HEFS = [
        "scdepthv3.hef"
    ]

    H8L_HEFS = [
        "scdepthv3.hef"
    ]
    hef_list = H8L_HEFS
    if architecture == 'hailo8':
        hef_list =  H8_HEFS
        return [os.path.join("resources","models","hailo8", hef) for hef in hef_list]

    return [os.path.join("resources","models","hailo8l", hef) for hef in hef_list]

def test_all_pipelines():
    """
    Combined test function for basic pipeline defaults.
    If architecture is hailo8, it will also test with hailo8l compatible HEFs.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    pipeline_list = get_pipelines_list()
    arch = get_device_architecture()
    arch_parameter_list = [""] # Test with default architecture
    logging.info(f"Detected Hailo architecture: {arch}")
    if arch == "hailo8":
        logging.info("Testing also with hailo8l compatible HEFs")
        arch_parameter_list.append("hailo8l") # Test with hailo8l architecture
    for arch_parameter in arch_parameter_list:
        if arch_parameter != "":
            arch_flag = f"--arch {arch_parameter}"
        for pipeline in pipeline_list:
            # Test with video input
            log_file_path = os.path.join(log_dir, f"test_{pipeline}{arch_parameter}_video_test.log")
            with open(log_file_path, "w") as log_file:
                cmd = ['python', '-u', f'basic_pipelines/{pipeline}']
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logging.info(f"Running {pipeline} {arch_parameter} with video input")
                try:
                    time.sleep(TEST_RUN_TIME)
                    process.send_signal(signal.SIGTERM)
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    pytest.fail(f"{pipeline} (video input) could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")

                stdout, stderr = process.communicate()
                log_file.write(f"{pipeline} (video input) stdout:\n{stdout.decode()}\n")
                log_file.write(f"{pipeline} (video input) stderr:\n{stderr.decode()}\n")

                assert "Traceback" not in stderr.decode(), f"{pipeline} (video input) encountered an exception: {stderr.decode()}"
                assert "Error" not in stderr.decode(), f"{pipeline} (video input) encountered an error: {stderr.decode()}"
                assert "frame" in stdout.decode().lower(), f"{pipeline} (video input) did not process any frames"
                if "depth" not in pipeline:
                    assert "detection" in stdout.decode().lower(), f"{pipeline} (video input) did not make any detections"

def test_all_pipelines_cameras():
    """
    Combined test function for basic pipeline scripts with different input sources.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    available_cameras = get_usb_video_devices()
    pipeline_list = get_pipelines_list()
    if rpi_camera_available:
        available_cameras.append("rpi")
    for pipeline in pipeline_list:
        # Test with available cameras
        for device in available_cameras:
            # if device is /dev/video* device name should be video*
            if device.startswith("/dev/video"):
                device_name = device.split("/")[-1]
            else:
                device_name = device
            log_file_path = os.path.join(log_dir, f"test_{pipeline}_{device_name}_camera_test.log")
            logging.info(f"Running {pipeline} with {device} camera")
            with open(log_file_path, "w") as log_file:
                cmd = ['python', '-u', f'basic_pipelines/{pipeline}', '--input', device]
                if pipeline == "instance_segmentation.py":
                    cmd += ['--labels-json', 'local_resources/yolov5m_seg.json']
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    time.sleep(TEST_RUN_TIME)
                    process.send_signal(signal.SIGTERM)
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    pytest.fail(f"{pipeline} ({device} camera) could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")
                stdout, stderr = process.communicate()
                log_file.write(f"{pipeline} ({device} camera) stdout:\n{stdout.decode()}\n")
                log_file.write(f"{pipeline} ({device} camera) stderr:\n{stderr.decode()}\n")
                assert "Traceback" not in stderr.decode(), f"{pipeline} ({device} camera) encountered an exception: {stderr.decode()}"
                assert "Error" not in stderr.decode(), f"{pipeline} ({device} camera) encountered an error: {stderr.decode()}"

    # Check if expected cameras are available
    if len(available_cameras) == 0:
        pytest.fail(f"No available cameras found for testing")
    if len(available_cameras) < 2 and rpi_camera_available:
        pytest.fail(f"Only one camera found for testing, both USB or RPi camera is required")

def test_all_pipelines_usb_camera():
    """
    Combined test function for basic pipeline scripts with usb as input source.
    """
    if len(get_usb_video_devices()) == 0:
        pytest.fail(f"No available cameras found for testing")
    log_dir = "logs"
    device = 'usb'
    os.makedirs(log_dir, exist_ok=True)
    pipeline_list = get_pipelines_list()
    for pipeline in pipeline_list:
        log_file_path = os.path.join(log_dir, f"test_{pipeline}_{device}_camera_test.log")
        logging.info(f"Running {pipeline} with {device} camera")
        with open(log_file_path, "w") as log_file:
            cmd = ['python', '-u', f'basic_pipelines/{pipeline}', '--input', device]
            if pipeline == "instance_segmentation.py":
                    cmd += ['--labels-json', 'local_resources/yolov5m_seg.json']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(TEST_RUN_TIME)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"{pipeline} ({device} camera) could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")
            stdout, stderr = process.communicate()
            log_file.write(f"{pipeline} ({device} camera) stdout:\n{stdout.decode()}\n")
            log_file.write(f"{pipeline} ({device} camera) stderr:\n{stderr.decode()}\n")
            assert "Traceback" not in stderr.decode(), f"{pipeline} ({device} camera) encountered an exception: {stderr.decode()}"
            assert "Error" not in stderr.decode(), f"{pipeline} ({device} camera) encountered an error: {stderr.decode()}"

def test_detection_hefs():
    """
    Combined test function for basic pipeline scripts with different HEFs and input sources.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    architecture = get_device_architecture()
    compatible_hefs = get_detection_compatible_hefs(architecture)
    for hef in compatible_hefs:
        hef_name = os.path.basename(hef)

        # Test with video input
        log_file_path = os.path.join(log_dir, f"detection_{hef_name}_video_test.log")
        logging.info(f"Running detection with {hef_name} (video input)")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(['python', 'basic_pipelines/detection.py', '--input', 'resources/videos/example.mp4', '--hef-path', hef],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(TEST_RUN_TIME)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"Detection with {hef_name} (video input) could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")

            stdout, stderr = process.communicate()
            log_file.write(f"Detection with {hef_name} (video input) stdout:\n{stdout.decode()}\n")
            log_file.write(f"Detection with {hef_name} (video input) stderr:\n{stderr.decode()}\n")

            assert "Traceback" not in stderr.decode(), f"Detection with {hef_name} (video input) encountered an exception: {stderr.decode()}"
            assert "Error" not in stderr.decode(), f"Detection with {hef_name} (video input) encountered an error: {stderr.decode()}"
            assert "frame" in stdout.decode().lower(), f"Detection with {hef_name} (video input) did not process any frames"
            assert "detection" in stdout.decode().lower(), f"Detection with {hef_name} (video input) did not make any detections"

def test_simple_detection_hefs():
    """
    Combined test function for basic pipeline scripts with different HEFs and input sources.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    architecture = get_device_architecture()
    compatible_hefs = get_detection_compatible_hefs(architecture)
    for hef in compatible_hefs:
        hef_name = os.path.basename(hef)

        # Test with video input
        log_file_path = os.path.join(log_dir, f"simple_detection_{hef_name}_video_test.log")
        logging.info(f"Running simple detection with {hef_name} (video input)")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(['python', '-u', 'basic_pipelines/detection_simple.py', '--input', 'resources/videos/example.mp4', '--hef-path', hef],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(TEST_RUN_TIME)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"Simple detection with {hef_name} (video input) could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")

            stdout, stderr = process.communicate()
            log_file.write(f"Simple detection with {hef_name} (video input) stdout:\n{stdout.decode()}\n")
            log_file.write(f"Simple detection with {hef_name} (video input) stderr:\n{stderr.decode()}\n")

            assert "Traceback" not in stderr.decode(), f"Simple detection with {hef_name} (video input) encountered an exception: {stderr.decode()}"
            assert "Error" not in stderr.decode(), f"Simple detection with {hef_name} (video input) encountered an error: {stderr.decode()}"
            assert "frame" in stdout.decode().lower(), f"Simple detection with {hef_name} (video input) did not process any frames"
            assert "detection" in stdout.decode().lower(), f"Simple detection with {hef_name} (video input) did not make any detections"

def test_pose_hefs():
    """
    Combined test function for basic pipeline scripts with different HEFs and input sources.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    architecture = get_device_architecture()
    compatible_hefs = get_pose_compatible_hefs(architecture)
    for hef in compatible_hefs:
        hef_name = os.path.basename(hef)

        # Test with video input
        log_file_path = os.path.join(log_dir, f"pose_{hef_name}_video_test.log")
        logging.info(f"Running pose with {hef_name} (video input)")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(['python', 'basic_pipelines/pose_estimation.py', '--input', 'resources/videos/example.mp4', '--hef-path', hef],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(TEST_RUN_TIME)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"pose with {hef_name} (video input) could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")

            stdout, stderr = process.communicate()
            log_file.write(f"pose with {hef_name} (video input) stdout:\n{stdout.decode()}\n")
            log_file.write(f"pose with {hef_name} (video input) stderr:\n{stderr.decode()}\n")

            assert "Traceback" not in stderr.decode(), f"pose with {hef_name} (video input) encountered an exception: {stderr.decode()}"
            assert "Error" not in stderr.decode(), f"pose with {hef_name} (video input) encountered an error: {stderr.decode()}"
            assert "frame" in stdout.decode().lower(), f"pose with {hef_name} (video input) did not process any frames"
            assert "detection" in stdout.decode().lower(), f"pose with {hef_name} (video input) did not make any detections"

def test_seg_hefs():
    """
    Combined test function for basic pipeline scripts with different HEFs and input sources.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    architecture = get_device_architecture()
    compatible_hefs = get_seg_compatible_hefs(architecture)
    for hef in compatible_hefs:
        hef_name = os.path.basename(hef)
        hef_base_name = os.path.splitext(hef_name)[0]


        # Test with video input
        log_file_path = os.path.join(log_dir, f"seg_{hef_name}_video_test.log")
        logging.info(f"Running seg with {hef_name} (video input)")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(['python', 'basic_pipelines/instance_segmentation.py', '--input', 'resources/videos/example.mp4', '--hef-path', hef],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(TEST_RUN_TIME)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"seg with {hef_name} (video input) could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")

            stdout, stderr = process.communicate()
            log_file.write(f"seg with {hef_name} (video input) stdout:\n{stdout.decode()}\n")
            log_file.write(f"seg with {hef_name} (video input) stderr:\n{stderr.decode()}\n")

            assert "Traceback" not in stderr.decode(), f"seg with {hef_name} (video input) encountered an exception: {stderr.decode()}"
            assert "Error" not in stderr.decode(), f"seg with {hef_name} (video input) encountered an error: {stderr.decode()}"
            assert "frame" in stdout.decode().lower(), f"seg with {hef_name} (video input) did not process any frames"
            assert "detection" in stdout.decode().lower(), f"seg with {hef_name} (video input) did not make any detections"

def test_depth_hefs():
    """
    Combined test function for basic pipeline scripts with different HEFs and input sources.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    architecture = get_device_architecture()
    compatible_hefs = get_depth_compatible_hefs(architecture)
    for hef in compatible_hefs:
        hef_name = os.path.basename(hef)

        # Test with video input
        log_file_path = os.path.join(log_dir, f"depth_{hef_name}_video_test.log")
        logging.info(f"Running depth with {hef_name} (video input)")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(['python', '-u', 'basic_pipelines/depth.py', '--input', 'resources/videos/example.mp4', '--hef-path', hef], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(TEST_RUN_TIME)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"depth with {hef_name} (video input) could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")

            stdout, stderr = process.communicate()
            log_file.write(f"depth with {hef_name} (video input) stdout:\n{stdout.decode()}\n")
            log_file.write(f"depth with {hef_name} (video input) stderr:\n{stderr.decode()}\n")

            assert "Traceback" not in stderr.decode(), f"depth with {hef_name} (video input) encountered an exception: {stderr.decode()}"
            assert "Error" not in stderr.decode(), f"depth with {hef_name} (video input) encountered an error: {stderr.decode()}"
            assert "frame" in stdout.decode().lower(), f"depth with {hef_name} (video input) did not process any frames"

def test_frame_rate():
    """Test that pipelines honor the --frame-rate flag by checking output FPS values"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    pipeline_list = get_pipelines_list()
    for pipeline in pipeline_list:
        # Test with video input
        log_file_path = os.path.join(log_dir, f"test_{pipeline}_frame_rate_test.log")
        logging.info(f"Running {pipeline} with frame rate flag")
        with open(log_file_path, "w") as log_file:
            cmd = ['python', '-u', f'basic_pipelines/{pipeline}', '--frame-rate', '10', '--show-fps']
            if pipeline == "instance_segmentation.py":
                cmd += ['--labels-json', 'local_resources/yolov5m_seg.json']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(TEST_RUN_TIME)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"{pipeline} (frame rate) could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")
            stdout, stderr = process.communicate()
            stdout_str = stdout.decode()
            stderr_str = stderr.decode()

            # Log outputs
            log_file.write(f"{pipeline} (frame rate) stdout:\n{stdout_str}\n")
            log_file.write(f"{pipeline} (frame rate) stderr:\n{stderr_str}\n")

            # Check for errors
            assert "Traceback" not in stderr_str, f"{pipeline} (frame rate) encountered an exception: {stderr_str}"
            assert "Error" not in stderr_str, f"{pipeline} (frame rate) encountered an error: {stderr_str}"

            # Extract FPS values using regex
            fps_pattern = re.compile(r'FPS: (\d+\.\d+)')
            fps_matches = fps_pattern.findall(stdout_str)

            # Only check FPS if we found some values
            if fps_matches:
                # Convert matches to float values
                fps_values = [float(match) for match in fps_matches]

                # Skip first few values as they might be during startup
                if len(fps_values) > 3:
                    fps_values = fps_values[3:]

                # Calculate average FPS
                avg_fps = sum(fps_values) / len(fps_values)
                log_file.write(f"Average FPS: {avg_fps:.2f}\n")

                # Assert that average FPS is within acceptable range of target (10)
                # Using a 10% tolerance
                #assert 9.0 <= avg_fps <= 11.0, f"FPS not within expected range. Got average {avg_fps:.2f}, expected around 10.0"
                logging.info(f"{pipeline} FPS test passed with average FPS of {avg_fps:.2f}")

# def test_pipeline_with_use_frame():
#     """
#     Combined test function for pipelines with the --use-frame flag, using a camera as the input source.
#     """
#     TEST_RUN_TIME = 10  # Run time set to 10 seconds
#     log_dir = "logs"
#     os.makedirs(log_dir, exist_ok=True)
#     pipeline_list = get_pipelines_list()

#     # Set the camera input source (update this based on your camera type)
#     camera_input = "/dev/video0"  # USB camera example; use "rpi" if it's a Raspberry Pi camera

#     for pipeline in pipeline_list:
#         # Set up logging for each pipeline
#         log_file_path = os.path.join(log_dir, f"{pipeline}_use_frame_camera_test.log")
#         with open(log_file_path, "w") as log_file:
#             cmd = ['python', '-u', f'basic_pipelines/{pipeline}', '--use-frame', '--input', camera_input]

#             # Start the process
#             process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#             logging.info(f"Running {pipeline} with --use-frame flag using camera input")

#             try:
#                 # Let the process run for the specified test time
#                 time.sleep(TEST_RUN_TIME)

#                 # Attempt to terminate the process
#                 process.send_signal(signal.SIGTERM)

#                 try:
#                     # Wait for process to exit and capture output within a timeout
#                     stdout, stderr = process.communicate(timeout=5)
#                 except subprocess.TimeoutExpired:
#                     # If process does not terminate, kill it
#                     process.kill()
#                     stdout, stderr = process.communicate()
#                     pytest.fail(f"{pipeline} with --use-frame flag could not be terminated within 5 seconds after running for {TEST_RUN_TIME} seconds")

#                 # Decode outputs
#                 stdout_str, stderr_str = stdout.decode(), stderr.decode()

#                 # Write output to log file
#                 log_file.write(f"{pipeline} with --use-frame flag stdout:\n{stdout_str}\n")
#                 log_file.write(f"{pipeline} with --use-frame flag stderr:\n{stderr_str}\n")

#                 # Assertions to check for errors in stderr and expected output in stdout
#                 assert "Traceback" not in stderr_str, f"{pipeline} with --use-frame flag encountered an exception: {stderr_str}"
#                 assert "Error" not in stderr_str, f"{pipeline} with --use-frame flag encountered an error: {stderr_str}"
#                 assert "frame" in stdout_str.lower(), f"{pipeline} with --use-frame flag did not process any frames"
#                 assert "detection" in stdout_str.lower(), f"{pipeline} with --use-frame flag did not make any detections"

#                 # Log that the test completed successfully for this pipeline
#                 log_file.write(f"{pipeline} with --use-frame flag test passed: completed without errors.\n")
#                 logging.info(f"{pipeline} with --use-frame flag test completed successfully.")

#             except Exception as e:
#                 # Ensure any exceptions are logged before failing
#                 logging.error(f"Error occurred in test for {pipeline} with --use-frame flag: {e}")
#                 pytest.fail(f"Test for {pipeline} with --use-frame flag failed due to unexpected error: {e}")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
