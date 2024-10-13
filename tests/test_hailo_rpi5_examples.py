# tests/test_advanced.py
import pytest
import subprocess
import os
import sys
import importlib
import time
import signal
import glob
from picamera2 import Picamera2
#from picamera2.previews import Preview


def test_environment():
    """Test the Python environment and required packages."""
    # Check Python version
    assert sys.version_info >= (3, 6), "Python 3.6 or higher is required."
    
    # Check for required Python packages
    required_packages = ['gi', 'numpy', 'opencv-python', 'setproctitle', 'hailo']
    for package in required_packages:
        try:
            if package == 'opencv-python':
                import cv2
                print(f"opencv-python is installed. Version: {cv2.__version__}")
            else:
                importlib.import_module(package)
                print(f"{package} is installed.")
        except ImportError:
            pytest.fail(f"{package} is not installed.")


def test_gstreamer_installation():
    """Test GStreamer installation."""
    try:
        subprocess.run(['gst-inspect-1.0', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        pytest.fail("GStreamer is not installed or not in PATH.")


def test_hailo_runtime():
    """Test Hailo runtime installation."""
    try:
        subprocess.run(['hailortcli', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        pytest.fail("Hailo runtime is not installed or not in PATH.")


def test_required_files():
    """Test for the presence of required files."""
    required_files = [
        'setup_env.sh',
        'download_resources.sh',
        'compile_postprocess.sh',
        'requirements.txt',
        'basic_pipelines/detection.py',
        'basic_pipelines/pose_estimation.py',
        'basic_pipelines/instance_segmentation.py',
        'basic_pipelines/hailo_rpi_common.py'
    ]
    for file in required_files:
        assert os.path.exists(file), f"{file} is missing."


def test_setup_env():
    """Test setup_env.sh script."""
    result = subprocess.run(['bash', '-c', 'source setup_env.sh && env'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout_str = result.stdout
    stderr_str = result.stderr

    print(f"Setup Environment stdout:\n{stdout_str}")
    print(f"Setup Environment stderr:\n{stderr_str}")
    
    assert 'TAPPAS_POST_PROC_DIR' in stdout_str, "TAPPAS_POST_PROC_DIR is not set by setup_env.sh"
    assert 'DEVICE_ARCHITECTURE' in stdout_str, "DEVICE_ARCHITECTURE is not set by setup_env.sh"


def test_combined_pipeline():
    """
    Combined test function for basic pipeline scripts and camera pipelines.
    Tests help messages, basic pipeline runs, and camera pipeline runs.
    """
    # Create logs directory
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Test help messages
    scripts = ["detection.py", "pose_estimation.py", "instance_segmentation.py"]
    for script in scripts:
        result = subprocess.run(['python', f'basic_pipelines/{script}', '--help'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert "usage:" in result.stdout, f"{script} help message not displayed correctly."

    # Test basic pipeline runs
    for script in scripts:
        log_file_path = os.path.join(log_dir, f"{script}_test.log")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(['python', f'basic_pipelines/{script}', '--input', 'resources/detection0.mp4'],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(30)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"{script} could not be terminated within 5 seconds after running for 30 seconds")

            stdout, stderr = process.communicate()
            stderr_str = stderr.decode()
            stdout_str = stdout.decode()

            log_file.write(f"{script} stdout full output (first 30 seconds):\n{stdout_str}\n")
            log_file.write(f"{script} stderr full output (first 30 seconds):\n{stderr_str}\n")

            if "HEF was compiled for Hailo8L device" in stderr_str:
                log_file.write(f"Warning: {script} - HEF compiled for Hailo8L device, may result in lower performance.\n")
            if "Config file doesn't exist" in stderr_str:
                log_file.write(f"Warning: {script} - Config file not found, using default parameters.\n")

            assert "Traceback" not in stderr_str, f"{script} encountered an exception: {stderr_str}"
            assert "Error" not in stderr_str, f"{script} encountered an error: {stderr_str}"
            assert "frame" in stdout_str.lower(), f"{script} did not process any frames within the first 30 seconds"
            assert "detection" in stdout_str.lower(), f"{script} did not make any detections within the first 30 seconds"

            log_file.write(f"{script} test passed: at least one frame and one detection processed.\n")

    # Test camera pipeline runs
    camera_types = ["usb", "rpi"]
    for camera_type in camera_types:
        log_file_path = os.path.join(log_dir, f"{camera_type}_camera_test.log")
        input_source = "/dev/video0" if camera_type == "usb" else "rpi_camera"

        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(['python', 'basic_pipelines/detection.py', '--input', input_source],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(20)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"{camera_type} camera pipeline could not be terminated within 5 seconds after running for 20 seconds")

            stdout, stderr = process.communicate()
            stderr_str = stderr.decode()
            stdout_str = stdout.decode()

            log_file.write(f"{camera_type} camera stdout full output (first 20 seconds):\n{stdout_str}\n")
            log_file.write(f"{camera_type} camera stderr full output (first 20 seconds):\n{stderr_str}\n")

            if "HEF was compiled for Hailo8L device" in stderr_str:
                log_file.write(f"Warning: {camera_type} camera - HEF compiled for Hailo8L device, may result in lower performance.\n")
            if "Config file doesn't exist" in stderr_str:
                log_file.write(f"Warning: {camera_type} camera - Config file not found, using default parameters.\n")

            assert "Traceback" not in stderr_str, f"{camera_type} camera encountered an exception: {stderr_str}"
            assert "Error" not in stderr_str, f"{camera_type} camera encountered an error: {stderr_str}"

            log_file.write(f"{camera_type} camera test passed: no critical errors encountered.\n")

# Register custom mark
pytest.mark.camera = pytest.mark.camera

def get_camera_indices():
    """Get a list of available video devices."""
    result = subprocess.run(['ls', '/dev/video*'], capture_output=True, text=True)
    devices = result.stdout.strip().split('\n')
    return devices

def identify_camera(device):
    """Identify the type of camera by querying its capabilities using v4l2-ctl."""
    try:
        result = subprocess.run(['v4l2-ctl', '--device', device, '--all'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout = result.stdout
        if "bcm2835" in stdout:
            return "Pi Camera"
        elif "USB" in stdout:
            return "USB Camera"
        else:
            return "Unknown Camera"
    except Exception as e:
        return f"Error identifying camera: {e}"

def test_camera_10_seconds(device):
    """Run the camera for 10 seconds and display output on the Raspberry Pi display."""
    try:
        picam2 = Picamera2(device)
        # preview = Preview(picam2)  # Comment this out if Preview is not available
        picam2.configure(picam2.create_preview_configuration())
        # picam2.start_preview(preview)  # Comment this out if Preview is not available
        picam2.start()
        
        print(f"Displaying camera feed from {device} for 10 seconds...")
        time.sleep(10)
        
        # picam2.stop_preview()  # Comment this out if Preview is not available
        picam2.stop()
        print(f"Successfully displayed camera feed from {device}")
        return True
    except Exception as e:
        print(f"Error testing camera at {device}: {e}")
        return False

def test_camera_pipeline(device, camera_type):
    """Test camera using the provided pipeline script."""
    print(f"Testing {camera_type} at {device}")
    process = subprocess.Popen(['python', 'basic_pipelines/detection.py', '--input', device], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(20)  # Run for 20 seconds
    finally:
        process.terminate()  # Gracefully terminate after 20 seconds
    try:
        process.wait(timeout=5)  # Wait up to 5 seconds for process termination
    except subprocess.TimeoutExpired:
        process.kill()  # Forcefully kill the process if it doesn't stop
    
    stdout, stderr = process.communicate()
    stdout_str = stdout.decode()
    stderr_str = stderr.decode()
    
    print(f"{camera_type} Test - Stdout:\n{stdout_str}")
    print(f"{camera_type} Test - Stderr:\n{stderr_str}")
    
    if "error" in stderr_str.lower():
        print(f"Unexpected error with {camera_type}: {stderr_str}")
        return False
    
    if process.returncode not in [0, -15]:
        print(f"{camera_type} process exited with unexpected code {process.returncode}")
        return False
    
    return True

@pytest.fixture
def camera_devices():
    return get_camera_indices()

@pytest.mark.camera
def test_camera_10_seconds_all(camera_devices):
    for device in camera_devices:
        assert test_camera_10_seconds(device)

@pytest.mark.camera
def test_camera_pipeline_all(camera_devices):
    for device in camera_devices:
        camera_type = identify_camera(device)
        assert test_camera_pipeline(device, camera_type)



if __name__ == "__main__":
    pytest.main(["-v", __file__])
