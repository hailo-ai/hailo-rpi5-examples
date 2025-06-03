# tests/test_infra.py
import pytest
import subprocess
import os
import sys
import time
import signal
import logging
from hailo_apps_infra.get_usb_camera import get_usb_video_devices
import numpy as np
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from unittest.mock import patch, MagicMock


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
        "yolov5m_wo_spp_h8l.hef",
        "yolov6n_h8l.hef",
        "yolov8s_h8l.hef",
        "yolov8m_h8l.hef",
        "yolov11n_h8l.hef",
        "yolov11s_h8l.hef"
    ]
    hef_list = H8L_HEFS
    if architecture == 'hailo8':
        hef_list = hef_list + H8_HEFS

    return [os.path.join("resources", hef) for hef in hef_list]

def get_pose_compatible_hefs(architecture):
    """Get a list of compatible HEF files based on the device architecture."""
    H8_HEFS = [
        "yolov8m_pose.hef",
        "yolov8s_pose.hef",
    ]

    H8L_HEFS = [
        "yolov8s_pose_h8l.hef",
    ]
    hef_list = H8L_HEFS
    if architecture == 'hailo8':
        hef_list = hef_list + H8_HEFS

    return [os.path.join("resources", hef) for hef in hef_list]

def get_seg_compatible_hefs(architecture):
    """Get a list of compatible HEF files based on the device architecture."""
    H8_HEFS = [
        "yolov5m_seg.hef",
        "yolov5n_seg.hef",
    ]

    H8L_HEFS = [
        "yolov5n_seg_h8l.hef",
    ]
    hef_list = H8L_HEFS
    if architecture == 'hailo8':
        hef_list = hef_list + H8_HEFS

    return [os.path.join("resources", hef) for hef in hef_list]

def get_depth_compatible_hefs(architecture):
    """Get a list of compatible HEF files based on the device architecture."""
    H8_HEFS = [
        "scdepthv3.hef"
    ]

    H8L_HEFS = [
        "scdepthv3_h8l.hef"
    ]
    hef_list = H8L_HEFS
    if architecture == 'hailo8':
        hef_list = hef_list + H8_HEFS

    return [os.path.join("resources", hef) for hef in hef_list]

def get_depth_compatible_hefs(architecture):
    """Get a list of compatible HEF files based on the device architecture."""
    H8_HEFS = [
        "scdepthv3.hef"
    ]

    H8L_HEFS = [
        "scdepthv3_h8l.hef"
    ]
    hef_list = H8L_HEFS
    if architecture == 'hailo8':
        hef_list = hef_list + H8_HEFS

    return [os.path.join("resources", hef) for hef in hef_list]

def test_detection_hefs():
    """Test detection pipeline with all compatible HEFs."""
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
            # Start process without redirecting output
            process = subprocess.Popen(
                ['python', '-m', 'hailo_apps_infra.detection_pipeline',
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
                log_file.write(f"Detection with {hef_name} completed successfully\n")
                log_file.write(f"Return code: {process.returncode}\n")
                
            except Exception as e:
                process.kill()
                pytest.fail(f"Test failed: {str(e)}")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()

def test_simple_detection_hefs():
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

def test_pose_hefs():
    """Test pose estimation pipeline with all compatible HEFs."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    architecture = get_device_architecture()
    compatible_hefs = get_pose_compatible_hefs(architecture)
    for hef in compatible_hefs:
        hef_name = os.path.basename(hef)

        log_file_path = os.path.join(log_dir, f"pose_{hef_name}_video_test.log")
        logging.info(f"Running pose estimation with {hef_name} (video input)")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(
                ['python', '-m', 'hailo_apps_infra.pose_estimation_pipeline',
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
                log_file.write(f"Pose estimation with {hef_name} completed successfully\n")
                log_file.write(f"Return code: {process.returncode}\n")
                
            except Exception as e:
                process.kill()
                pytest.fail(f"Test failed: {str(e)}")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()

def test_segmentation_hefs():
    """Test instance segmentation pipeline with all compatible HEFs."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    architecture = get_device_architecture()
    compatible_hefs = get_seg_compatible_hefs(architecture)
    for hef in compatible_hefs:
        hef_name = os.path.basename(hef)

        log_file_path = os.path.join(log_dir, f"segmentation_{hef_name}_video_test.log")
        logging.info(f"Running segmentation with {hef_name} (video input)")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(
                ['python', '-m', 'hailo_apps_infra.instance_segmentation_pipeline',
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
                log_file.write(f"Segmentation with {hef_name} completed successfully\n")
                log_file.write(f"Return code: {process.returncode}\n")
                
            except Exception as e:
                process.kill()
                pytest.fail(f"Test failed: {str(e)}")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()

def test_depth_hefs():
    """Test depth pipeline with all compatible HEFs."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    architecture = get_device_architecture()
    compatible_hefs = get_depth_compatible_hefs(architecture)
    for hef in compatible_hefs:
        hef_name = os.path.basename(hef)

        log_file_path = os.path.join(log_dir, f"depth_{hef_name}_video_test.log")
        logging.info(f"Running depth with {hef_name} (video input)")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(
                ['python', '-m', 'hailo_apps_infra.depth_pipeline',
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
                log_file.write(f"Depth with {hef_name} completed successfully\n")
                log_file.write(f"Return code: {process.returncode}\n")
                
            except Exception as e:
                process.kill()
                pytest.fail(f"Test failed: {str(e)}")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()

def test_rpi_camera():
    """Test all pipelines with RPI camera."""
    if not rpi_camera_available:
        pytest.skip("RPI camera not available")

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    arch = get_device_architecture()
    
    # Test each pipeline with RPI camera
    pipeline_configs = [
        ('detection_pipeline', get_detection_compatible_hefs(arch)),
        ('detection_pipeline_simple', get_detection_compatible_hefs(arch)),
        ('pose_estimation_pipeline', get_pose_compatible_hefs(arch)),
        ('instance_segmentation_pipeline', get_seg_compatible_hefs(arch)),
        ('depth_pipeline', get_depth_compatible_hefs(arch))
    ]

    for pipeline_name, hefs in pipeline_configs:
        if not hefs:
            continue

        hef = hefs[0]  # Use first compatible HEF
        log_file_path = os.path.join(log_dir, f"{pipeline_name}_rpi_test.log")
        
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(
                ['python', '-m', f'hailo_apps_infra.{pipeline_name}',
                '--input', 'rpi',
                '--hef-path', hef,
                '--show-fps'])
            
            try:
                time.sleep(TEST_RUN_TIME)
                process.send_signal(signal.SIGTERM)
                
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                
                assert process.returncode == 0 or process.returncode == -15, \
                    f"Process failed with return code {process.returncode}"
                
                log_file.write(f"{pipeline_name} with RPI camera completed successfully\n")
                log_file.write(f"Return code: {process.returncode}\n")
                
            except Exception as e:
                process.kill()
                pytest.fail(f"Test failed: {str(e)}")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()

from hailo_apps_infra.hailo_rpi_common import (
    detect_hailo_arch,
    get_caps_from_pad,
    get_default_parser,
    handle_rgb,
    handle_nv12,
    handle_yuyv,
    get_numpy_from_buffer
)

# Initialize GStreamer
Gst.init(None)

def test_get_caps_from_pad():
    """Test the GStreamer pad capabilities extraction function."""
    # Create a mock pad with caps
    pad = MagicMock(spec=Gst.Pad)
    caps = Gst.Caps.from_string("video/x-raw,format=RGB,width=1920,height=1080")
    pad.get_current_caps.return_value = caps
    
    format, width, height = get_caps_from_pad(pad)
    assert format == "RGB"
    assert width == 1920
    assert height == 1080

    # Test with no caps
    pad.get_current_caps.return_value = None
    format, width, height = get_caps_from_pad(pad)
    assert format is None
    assert width is None
    assert height is None

def test_get_default_parser():
    """Test the argument parser configuration."""
    parser = get_default_parser()
    
    # Test default values
    args = parser.parse_args([])
    assert not args.use_frame
    assert args.input is None
    assert not args.show_fps
    assert args.arch is None
    assert args.hef_path is None
    assert not args.disable_sync
    assert not args.dump_dot

    # Test custom values
    args = parser.parse_args([
        "-i", "test.mp4",
        "-u",
        "-f",
        "--arch", "hailo8",
        "--hef-path", "model.hef",
        "--disable-sync",
        "--dump-dot"
    ])
    assert args.input == "test.mp4"
    assert args.use_frame
    assert args.show_fps
    assert args.arch == "hailo8"
    assert args.hef_path == "model.hef"
    assert args.disable_sync
    assert args.dump_dot

def test_handle_rgb():
    """Test RGB format handling."""
    width, height = 2, 2
    test_data = np.array([[[1, 2, 3], [4, 5, 6]],
                         [[7, 8, 9], [10, 11, 12]]], dtype=np.uint8)
    
    class MockMapInfo:
        def __init__(self, data):
            self.data = data.tobytes()
    
    map_info = MockMapInfo(test_data)
    result = handle_rgb(map_info, width, height)
    
    assert isinstance(result, np.ndarray)
    assert result.shape == (height, width, 3)
    np.testing.assert_array_equal(result, test_data)

def test_handle_nv12():
    """Test NV12 format handling."""
    width, height = 2, 2
    y_plane = np.array([[1, 2],
                       [3, 4]], dtype=np.uint8)
    uv_plane = np.array([[[5, 6]]], dtype=np.uint8)
    
    combined_data = np.concatenate([y_plane.flatten(), uv_plane.flatten()])
    
    class MockMapInfo:
        def __init__(self, data):
            self.data = data.tobytes()
    
    map_info = MockMapInfo(combined_data)
    y_result, uv_result = handle_nv12(map_info, width, height)
    
    assert isinstance(y_result, np.ndarray)
    assert isinstance(uv_result, np.ndarray)
    assert y_result.shape == (height, width)
    assert uv_result.shape == (height//2, width//2, 2)
    np.testing.assert_array_equal(y_result, y_plane)
    np.testing.assert_array_equal(uv_result, uv_plane)

def test_handle_yuyv():
    """Test YUYV format handling."""
    width, height = 2, 2
    test_data = np.array([[[1, 2], [3, 4]],
                         [[5, 6], [7, 8]]], dtype=np.uint8)
    
    class MockMapInfo:
        def __init__(self, data):
            self.data = data.tobytes()
    
    map_info = MockMapInfo(test_data)
    result = handle_yuyv(map_info, width, height)
    
    assert isinstance(result, np.ndarray)
    assert result.shape == (height, width, 2)
    np.testing.assert_array_equal(result, test_data)

def test_get_numpy_from_buffer():
    """Test buffer to numpy array conversion."""
    width, height = 2, 2
    test_data = np.array([[[1, 2, 3], [4, 5, 6]],
                         [[7, 8, 9], [10, 11, 12]]], dtype=np.uint8)
    
    # Create a mock buffer
    class MockBuffer:
        def map(self, flags):
            class MockMapInfo:
                def __init__(self, data):
                    self.data = data
            return True, MockMapInfo(test_data.tobytes())
        
        def unmap(self, map_info):
            pass
    
    mock_buffer = MockBuffer()
    
    # Test RGB format
    result = get_numpy_from_buffer(mock_buffer, 'RGB', width, height)
    assert isinstance(result, np.ndarray)
    assert result.shape == (height, width, 3)
    np.testing.assert_array_equal(result, test_data)
    
    # Test unsupported format
    with pytest.raises(ValueError, match="Unsupported format"):
        get_numpy_from_buffer(mock_buffer, 'UNSUPPORTED', width, height)

if __name__ == "__main__":
    pytest.main(["-v", __file__])