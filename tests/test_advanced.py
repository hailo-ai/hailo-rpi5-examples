# tests/test_advanced.py
import pytest
import subprocess
import time

def run_pipeline(script, input_source, duration=30):
    """Helper function to run a pipeline for a specified duration."""
    process = subprocess.Popen(['python', f'basic_pipelines/{script}', '--input', input_source],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(duration)
    process.terminate()
    stdout, stderr = process.communicate()
    return stdout.decode(), stderr.decode()

@pytest.mark.performance
def test_inference_speed():
    """Test inference speed for each model."""
    models = ['detection.py', 'pose_estimation.py', 'instance_segmentation.py']
    for model in models:
        stdout, _ = run_pipeline(model, 'resources/detection0.mp4', duration=60)
        fps_lines = [line for line in stdout.split('\n') if 'FPS:' in line]
        fps_values = [float(line.split(':')[1].split(',')[0]) for line in fps_lines]
        avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
        assert avg_fps > 10, f"Average FPS for {model} is below 10 FPS: {avg_fps}"

@pytest.mark.stress
def test_long_running():
    """Test long-running stability."""
    script = 'detection.py'
    process = subprocess.Popen(['python', f'basic_pipelines/{script}', '--input', 'resources/detection0.mp4'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start_time = time.time()
    try:
        while time.time() - start_time < 3600:  # Run for 1 hour
            if process.poll() is not None:
                raise AssertionError(f"Process exited unexpectedly after {time.time() - start_time} seconds")
            time.sleep(10)
    finally:
        process.terminate()
        stdout, stderr = process.communicate()
    assert "Error" not in stderr.decode(), f"Errors encountered during long-running test: {stderr.decode()}"
