# tests/test_advanced.py
import glob
import pytest
import subprocess
import time
import os
import signal
from test_hailo_rpi5_examples import get_device_architecture, get_detection_compatible_hefs

def run_pipeline(script, input_source, duration=30, additional_args=None):
    cmd = ['python', '-u', f'basic_pipelines/{script}', '--input', input_source]
    if additional_args:
        cmd.extend(additional_args)

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(duration)
    finally:
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=5)
    stdout, stderr = process.communicate()

    print(f"--- Pipeline Output for {script} ---")
    print(stdout.decode())
    print(stderr.decode())
    print("----------------------------------")

    return stdout.decode(), stderr.decode()

def run_download_resources():
    script_path = "./download_resources.sh"
    try:
        result = subprocess.run([script_path, "--all"], check=True, capture_output=True, text=True)
        print("Download resources output:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running download_resources.sh: {e}")
        print("Script output:", e.output)
        return Falseupstream

def test_inference_speed():
    models = ['detection.py', 'detection_simple.py', 'pose_estimation.py', 'instance_segmentation.py', 'depth.py']
    for model in models:
        stdout, _ = run_pipeline(model, 'resources/example.mp4', duration=60, additional_args=['--show-fps'])
        fps_lines = [line for line in stdout.split('\n') if 'FPS' in line or 'fps' in line]

        if not fps_lines:
            raise AssertionError(f"FPS data not found for {model}")

        fps_values = []
        for line in fps_lines:
            try:
                fps_values.append(float(line.split(':')[1].strip().split(',')[0]))
            except (ValueError, IndexError):
                print(f"Failed to parse FPS from line: {line}")

        avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
        assert avg_fps > 10, f"Average FPS for {model} is below 10 FPS: {avg_fps}"

def test_long_running():
    stdout, stderr = run_pipeline('detection.py', 'resources/example.mp4', duration=5)
    assert "Error" not in stderr, f"Errors encountered during long-running test: {stderr}"


def test_detection_pipeline_all_hefs():
    assert run_download_resources(), "Failed to download resources"

    arch = get_device_architecture()
    assert arch is not None, "Failed to detect Hailo architecture"
    print(f"Detected Hailo architecture: {arch}")

    detection_hefs = get_detection_compatible_hefs(arch)
    if not detection_hefs:
        print("No detection HEFs found. Listing all files in resources directory:")
        print(os.listdir("resources"))
        pytest.skip(f"No suitable detection HEFs found for {arch}")

    for hef_path in detection_hefs:
        print(f"Testing detection pipeline with HEF: {hef_path}")
        stdout, stderr = run_pipeline('detection.py', 'resources/example.mp4', duration=30, additional_args=['--hef-path', hef_path])

        assert "Traceback" not in stderr, f"Exception occurred with HEF {hef_path}: {stderr}"
        assert "Error" not in stderr, f"Error occurred with HEF {hef_path}: {stderr}"
        assert "frame" in stdout.lower(), f"No frames processed with HEF {hef_path}"
        assert "detection" in stdout.lower(), f"No detections made with HEF {hef_path}"

        print(f"Test passed for HEF: {hef_path}")

    print(f"All suitable detection HEFs for {arch} tested successfully")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
