import pytest
import os
import subprocess
import sys
import importlib
import time

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
            print(f"{package} is not installed.")

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
    assert 'TAPPAS_POST_PROC_DIR' in result.stdout, "TAPPAS_POST_PROC_DIR is not set by setup_env.sh"
    assert 'DEVICE_ARCHITECTURE' in result.stdout, "DEVICE_ARCHITECTURE is not set by setup_env.sh"

@pytest.mark.parametrize("script", ["detection.py", "pose_estimation.py", "instance_segmentation.py"])
def test_basic_pipeline_help(script):
    """Test if basic pipeline scripts run with --help flag."""
    result = subprocess.run(['python', f'basic_pipelines/{script}', '--help'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert "usage:" in result.stdout, f"{script} help message not displayed correctly."

@pytest.mark.parametrize("script", ["detection.py", "pose_estimation.py", "instance_segmentation.py"])
def test_basic_pipeline_run(script):
    """Test if basic pipeline scripts run without errors."""
    timeout = 30  # Increased timeout to 30 seconds
    process = subprocess.Popen(['python', f'basic_pipelines/{script}', '--input', 'resources/detection0.mp4'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        pytest.fail(f"{script} timed out after {timeout} seconds")

    stderr_str = stderr.decode()
    stdout_str = stdout.decode()

    # Check for HEF warning
    if "HEF was compiled for Hailo8L device" in stderr_str:
        print(f"Warning: {script} - HEF compiled for Hailo8L device, may result in lower performance.")

    # Check for config file warning in instance segmentation
    if script == "instance_segmentation.py" and "Config file doesn't exist" in stderr_str:
        print(f"Warning: {script} - Config file not found, using default parameters.")

    # Print stdout and stderr for debugging
    print(f"{script} stdout:", stdout_str)
    print(f"{script} stderr:", stderr_str)

    # Assert on specific error conditions, not just return code
    assert "Traceback" not in stderr_str, f"{script} encountered an exception: {stderr_str}"
    assert "Error" not in stderr_str, f"{script} encountered an error: {stderr_str}"

    # Check if the script produced any output indicating successful run
    assert "Processing frame" in stdout_str or "Processed" in stdout_str, f"{script} did not produce expected output"
    assert process.returncode == 0 or process.returncode is None, f"{script} exited with an error: {stderr.decode()}"

@pytest.mark.skipif(not os.path.exists('/dev/video0'), reason="No camera detected")
def test_camera_input():
    """Test camera input if available."""
    process = subprocess.Popen(['python', 'hailo-rpi5-examples/basic_pipelines/detection.py', '--input', '/dev/video0'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(20)  # Run for 20 seconds
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    
    stdout, stderr = process.communicate()
    print("Stdout:", stdout.decode())
    print("Stderr:", stderr.decode())
    
    # Check for HEF warning
    if "HEF was compiled for Hailo8L device" in stderr.decode():
        print("Warning: HEF compiled for Hailo8L device, may result in lower performance.")
    
    # Don't assert on return code, as we're intentionally terminating the process
    assert "error" not in stderr.decode().lower(), f"Unexpected error in stderr: {stderr.decode()}"

if __name__ == "__main__":
    pytest.main(["-v", __file__])