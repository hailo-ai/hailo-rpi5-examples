# tests/test_advanced.py
import pytest
import subprocess
import os
import sys
import importlib
import time
import signal

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


@pytest.mark.parametrize("script", ["detection.py", "pose_estimation.py", "instance_segmentation.py"])
def test_basic_pipeline_help(script):
    """Test if basic pipeline scripts run with --help flag."""
    result = subprocess.run(['python', f'basic_pipelines/{script}', '--help'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert "usage:" in result.stdout, f"{script} help message not displayed correctly."


@pytest.mark.parametrize("script", ["detection.py", "pose_estimation.py", "instance_segmentation.py"])
def test_basic_pipeline_run(script):
    """Test if basic pipeline scripts run without errors for 30 seconds and process at least one frame and one detection."""
    
    # Log file path (create a logs directory if it doesn't exist)
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f"{script}_test.log")
    
    with open(log_file_path, "w") as log_file:
        process = subprocess.Popen(['python', f'basic_pipelines/{script}', '--input', 'resources/detection0.mp4'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            # Let the process run for 30 seconds
            time.sleep(30)
            
            # After 30 seconds, terminate the process
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)  # Wait for up to 5 seconds for process to terminate
        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail(f"{script} could not be terminated within 5 seconds after running for 30 seconds")

        stdout, stderr = process.communicate()
        stderr_str = stderr.decode()
        stdout_str = stdout.decode()

        # Write output to log file
        log_file.write(f"{script} stdout full output (first 30 seconds):\n{stdout_str}\n")
        log_file.write(f"{script} stderr full output (first 30 seconds):\n{stderr_str}\n")

        # Check for warnings but allow them
        if "HEF was compiled for Hailo8L device" in stderr_str:
            log_file.write(f"Warning: {script} - HEF compiled for Hailo8L device, may result in lower performance.\n")
        if "Config file doesn't exist" in stderr_str:
            log_file.write(f"Warning: {script} - Config file not found, using default parameters.\n")

        # Ensure there were no exceptions or critical errors
        assert "Traceback" not in stderr_str, f"{script} encountered an exception: {stderr_str}"
        assert "Error" not in stderr_str, f"{script} encountered an error: {stderr_str}"

        # Check if at least one frame and one detection were processed
        assert "frame" in stdout_str.lower(), f"{script} did not process any frames within the first 30 seconds"
        assert "detection" in stdout_str.lower(), f"{script} did not make any detections within the first 30 seconds"

        log_file.write(f"{script} test passed: at least one frame and one detection processed.\n")
        


def identify_camera(device):
    """Identify the type of camera by querying its capabilities using v4l2-ctl."""
    try:
        result = subprocess.run(['v4l2-ctl', '--device', device, '--all'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout = result.stdout
        if "bcm2835" in stdout:  # Common identifier for the Pi Camera
            return "Pi Camera"
        elif "USB" in stdout:  # Common identifier for USB Cameras
            return "USB Camera"
        else:
            return "Unknown Camera"
    except Exception as e:
        return f"Error identifying camera: {e}"


def _test_camera(device, camera_type):
    """Helper function to test camera input for the given device (e.g., /dev/video0 or /dev/video1)."""
    print(f"Testing {camera_type} at {device}")
    
    # Run the pipeline on the camera device
    process = subprocess.Popen(['python', 'basic_pipelines/detection.py', '--input', device],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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

    # Print the captured stdout and stderr
    print(f"{camera_type} Test - Stdout:\n{stdout_str}")
    print(f"{camera_type} Test - Stderr:\n{stderr_str}")

    # Check for any unexpected errors in stderr
    assert "error" not in stderr_str.lower(), f"Unexpected error with {camera_type}: {stderr_str}"

    # Allow the process to exit with code 0 or -15 (SIGTERM due to intentional termination)
    assert process.returncode in [0, -15], f"{camera_type} process exited with unexpected code {process.returncode}"


def test_both_cameras():
    """Test both the Pi Camera and USB Camera."""
    devices = ['/dev/video0', '/dev/video1']  # Device paths for the cameras
    
    for device in devices:
        if os.path.exists(device):  # Check if the camera device exists
            camera_type = identify_camera(device)  # Identify the type of camera
            _test_camera(device, camera_type)  # Run the camera test
        else:
            pytest.skip(f"{device} not found, skipping.")  # Skip if the device is not found



if __name__ == "__main__":
    pytest.main(["-v", __file__])
