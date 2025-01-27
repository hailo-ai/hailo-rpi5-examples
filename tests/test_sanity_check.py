# tests/test_sanity_check.py
import pytest
import subprocess
import os
import sys
import importlib


def test_check_hailo_runtime_installed():
    """Test if the Hailo runtime is installed."""
    try:
        subprocess.run(['hailortcli', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Hailo runtime is installed.")
    except subprocess.CalledProcessError:
        pytest.fail("Error: Hailo runtime is not installed or not in PATH.")

def test_check_required_files():
    """Test if required files exist."""
    required_files = [
        'setup_env.sh',
        'download_resources.sh',
        'requirements.txt',
        'basic_pipelines/detection.py',
        'basic_pipelines/detection_simple.py',
        'basic_pipelines/pose_estimation.py',
        'basic_pipelines/instance_segmentation.py',
        'basic_pipelines/depth.py'
    ]
    for file in required_files:
        assert os.path.exists(file), f"Error: {file} is missing."

def test_environment():
    """Test the Python environment and required packages."""
    # Check Python version
    assert sys.version_info >= (3, 6), "Python 3.6 or higher is required."
    
    # Check for required Python packages
    required_packages = ['gi', 'numpy', 'opencv-python', 'setproctitle', 'hailo', 'hailo_apps_infra']
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

def test_setup_env():
    """Test setup_env.sh script."""
    result = subprocess.run(['bash', '-c', 'source setup_env.sh'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout_str = result.stdout
    stderr_str = result.stderr

    print(f"Setup Environment stdout:\n{stdout_str}")
    print(f"Setup Environment stderr:\n{stderr_str}")
    
    assert 'TAPPAS_POST_PROC_DIR' in stdout_str, "TAPPAS_POST_PROC_DIR is not set by setup_env.sh"
    assert 'DEVICE_ARCHITECTURE' in stdout_str, "DEVICE_ARCHITECTURE is not set by setup_env.sh"
