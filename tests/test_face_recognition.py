import pytest
import os
import subprocess

# region test sanity check
def test_check_required_files():
    """Test if required files exist."""
    required_files = [
        'community_projects/face_recognition/compile_postprocess.py',
        'community_projects/face_recognition/install.sh',
        'community_projects/face_recognition/meson.build',
        'community_projects/face_recognition/download_resources.sh',
        'community_projects/face_recognition/requirements.txt',
        'community_projects/face_recognition/app_db.py',
        'community_projects/face_recognition/db_handler.py',
        'community_projects/face_recognition/face_recognition_pipeline_db.py',
        'community_projects/face_recognition/web/web_app.py',
        'community_projects/face_recognition/web/templates/index.html'
    ]
    for file in required_files:
        assert os.path.exists(file), f"Error: {file} is missing."
# endregion

# region test edge cases
def run_pipeline_with_input(script, input_source):
    """Helper to run a pipeline script with a specific input."""
    process = subprocess.run(['python', f'community_projects/face_recognition/{script}', '--input', input_source],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def test_invalid_video_input():
    """Test invalid video input."""
    script = 'app_db.py'
    result = run_pipeline_with_input(script, 'invalid_path.mp4')
    if "No such file" in result.stderr:
        assert True, "The pipeline reported an error for an invalid video path."
    else:
        assert False, "The pipeline did not report an error for an invalid video path."

def test_unsupported_format():
    """Test unsupported input file format."""
    script = 'app_db.py'
    result = run_pipeline_with_input(script, 'tests/test_resources/dummy_text.txt')
    if "Can't typefind stream" in result.stderr:
        assert True, "The pipeline reported an error for unsupported input format."
    else:
        assert False, "The pipeline did not report an error for unsupported input format."

@pytest.mark.parametrize("script", ["app_db.py"])
def test_invalid_command_arguments(script):
    """Test how pipelines handle invalid command-line arguments."""
    process = subprocess.run(['python', f'community_projects/face_recognition/{script}', '--unknown_arg'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert "error: unrecognized arguments:" in process.stderr or "usage:" in process.stderr, \
        "Pipeline did not handle invalid command-line arguments correctly."
# endregion

# region test advanced
def run_pipeline(script, input_source, duration=30, additional_args=None):
    cmd = ['python', f'community_projects/face_recognition/{script}', '--input', input_source]
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
    script_path = "community_projects/face_recognition/download_resources.sh"
    try:
        result = subprocess.run([script_path, "--all"], check=True, capture_output=True, text=True)
        print("Download resources output:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running download_resources.sh: {e}")
        print("Script output:", e.output)
        return Falseupstream

def test_inference_speed():
    models = ['app_db.py']
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
# endregion

# region examples

# Adjust the sys.path to include the parent directory of the test folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from hailo_apps_infra.get_usb_camera import get_usb_video_devices

try:
    from picamera2 import Picamera2
    rpi_camera_available = True
except ImportError:
    rpi_camera_available = False

TEST_RUN_TIME = 10

def get_device_architecture():
    """Get the device architecture from hailortcli."""
    try:
        result = subprocess.run(['hailortcli', 'fw-control', 'identify'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if "Device Architecture" in line:
                return line.split(':')[1].strip().lower()
    except Exception:
        return "unknown"

def test_pipeline():
    """
    Combined test function for basic pipeline defaults.
    If architecture is hailo8, it will also test with hailo8l compatible HEFs.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    pipeline = "community_projects/face_recognition/face_recognition_pipeline_db.py"
    arch = get_device_architecture()
    arch_parameter_list = [""] # Test with default architecture
    logging.info(f"Detected Hailo architecture: {arch}")
    if arch == "hailo8":
        logging.info("Testing also with hailo8l compatible HEFs")
        arch_parameter_list.append("hailo8l") # Test with hailo8l architecture
    for arch_parameter in arch_parameter_list:
        if arch_parameter != "":
            arch_flag = f"--arch {arch_parameter}"
        # Test with video input
        log_file_path = os.path.join(log_dir, f"test_{pipeline}{arch_parameter}_video_test.log")
        with open(log_file_path, "w") as log_file:
            cmd = ['python', '-u', f'{pipeline}']

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
            assert "detection" in stdout.decode().lower(), f"{pipeline} (video input) did not make any detections"
# endregion

# region infra
def test_face_recognition():
    """Test simple detection pipeline with all compatible HEFs."""
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
            # Start process without redirecting output
            process = subprocess.Popen(
                ['python', '-m', 'hailo_apps_infra.detection_pipeline_simple',
                 '--input', 'resources/example.mp4',
                 '--hef-path', hef,
                 '--show-fps'])
            
            try:
                # Let it run
                time.sleep(TEST_RUN_TIME)
                
                # Gracefully terminate
                process.send_signal(signal.SIGTERM)
                
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                
                # Check return code
                assert process.returncode == 0 or process.returncode == -15, \
                    f"Process failed with return code {process.returncode}"
                
                # Write to log
                log_file.write(f"Simple detection with {hef_name} completed successfully\n")
                log_file.write(f"Return code: {process.returncode}\n")
                
            except Exception as e:
                process.kill()
                pytest.fail(f"Test failed: {str(e)}")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()

# endregion
