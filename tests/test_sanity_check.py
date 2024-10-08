# tests/test_sanity_check.py
import pytest
import subprocess
import os

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
        'compile_postprocess.sh',
        'requirements.txt',
        'basic_pipelines/detection.py',
        'basic_pipelines/pose_estimation.py',
        'basic_pipelines/instance_segmentation.py',
        'basic_pipelines/hailo_rpi_common.py'
    ]
    for file in required_files:
        assert os.path.exists(file), f"Error: {file} is missing."
