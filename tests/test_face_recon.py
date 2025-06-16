# region imports
# Standard library imports
import os
import logging

# Third-party imports
import pytest

# Local application-specific imports
from hailo_apps_infra.hailo_core.hailo_common.test_utils import run_pipeline_module_with_args, run_pipeline_pythonpath_with_args, run_pipeline_cli_with_args, get_pipeline_args
from hailo_apps_infra.hailo_core.hailo_common.installation_utils import detect_host_arch
from hailo_apps_infra.hailo_core.hailo_common.camera_utils import is_rpi_camera_available
# endregion imports

# Configure logging as needed.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_run_everything')
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Define pipeline configurations.
@pytest.fixture
def pipeline():
    return {
        'name': 'face_recognition',
        'script': 'hailo_rpi5_examples/apps/face_recognition/face_recognition.py',
        'cli': 'hailo-face-recon'
    }

# Map each run method label to its corresponding function.
run_methods = {
    'pythonpath': run_pipeline_pythonpath_with_args,
    'cli': run_pipeline_cli_with_args
}

@pytest.mark.parametrize('run_method_name', list(run_methods.keys()))
def test_train(pipeline, run_method_name):
    test_name = 'test_train'
    args = get_pipeline_args(suite='mode-train') 
    log_file_path = os.path.join(log_dir, f"{pipeline['name']}_{test_name}_{run_method_name}.log")
    
    if run_method_name == 'module':
        stdout, stderr = run_methods[run_method_name](pipeline['module'], args, log_file_path)
    elif run_method_name == 'pythonpath':
        stdout, stderr = run_methods[run_method_name](pipeline['script'], args, log_file_path)
    elif run_method_name == 'cli':
        stdout, stderr = run_methods[run_method_name](pipeline['cli'], args, log_file_path)
    else:
        pytest.fail(f"Unknown run method: {run_method_name}")
    
    out_str = stdout.decode().lower() if stdout else ""
    err_str = stderr.decode().lower() if stderr else ""
    print(f"Completed: {test_name}, {pipeline['name']}, {run_method_name}: {out_str}")
    assert 'error' not in err_str, f"{pipeline['name']} ({run_method_name}) reported an error in {test_name}: {err_str}"
    assert 'traceback' not in err_str, f"{pipeline['name']} ({run_method_name}) traceback in {test_name} : {err_str}"

@pytest.mark.parametrize('run_method_name', list(run_methods.keys()))
def test_default(pipeline, run_method_name):
    test_name = 'test_default'
    args = get_pipeline_args(suite='default') 
    log_file_path = os.path.join(log_dir, f"{pipeline['name']}_{test_name}_{run_method_name}.log")
    
    if run_method_name == 'module':
        stdout, stderr = run_methods[run_method_name](pipeline['module'], args, log_file_path)
    elif run_method_name == 'pythonpath':
        stdout, stderr = run_methods[run_method_name](pipeline['script'], args, log_file_path)
    elif run_method_name == 'cli':
        stdout, stderr = run_methods[run_method_name](pipeline['cli'], args, log_file_path)
    else:
        pytest.fail(f"Unknown run method: {run_method_name}")
    
    out_str = stdout.decode().lower() if stdout else ""
    err_str = stderr.decode().lower() if stderr else ""
    print(f"Completed: {test_name}, {pipeline['name']}, {run_method_name}: {out_str}")
    assert 'error' not in err_str, f"{pipeline['name']} ({run_method_name}) reported an error in {test_name}: {err_str}"
    assert 'traceback' not in err_str, f"{pipeline['name']} ({run_method_name}) traceback in {test_name} : {err_str}"

# @pytest.mark.parametrize('run_method_name', list(run_methods.keys()))
# def test_cli_rpi_viz(pipeline, run_method_name):
#     test_name = 'test_cli_rpi_viz'
#     args = get_pipeline_args(suite='rpi_camera,visualize')
#     rpi_device = is_rpi_camera_available()

#     if ('rpi' == detect_host_arch() and rpi_device):
#         log_file_path = os.path.join(log_dir, f"{pipeline['name']}_{test_name}_{run_method_name}.log")
        
#         if run_method_name == 'module':
#             stdout, stderr = run_methods[run_method_name](pipeline['module'], args, log_file_path)
#         elif run_method_name == 'pythonpath':
#             stdout, stderr = run_methods[run_method_name](pipeline['script'], args, log_file_path)
#         elif run_method_name == 'cli':
#             stdout, stderr = run_methods[run_method_name](pipeline['cli'], args, log_file_path)
#         else:
#             pytest.fail(f"Unknown run method: {run_method_name}")
        
#         out_str = stdout.decode().lower() if stdout else ""
#         err_str = stderr.decode().lower() if stderr else ""
#         print(f"Completed: {test_name}, {pipeline['name']}, {run_method_name}: {out_str}")
#         assert 'error' not in err_str, f"{pipeline['name']} ({run_method_name}) reported an error in {test_name}: {err_str}"
#         assert 'traceback' not in err_str, f"{pipeline['name']} ({run_method_name}) traceback in {test_name} : {err_str}"
#     else:
#         print('Not running on Raspberry Pi; skipping RPi camera run.')

# @pytest.mark.parametrize('run_method_name', list(run_methods.keys()))
# def test_ui_rpi_viz(pipeline, run_method_name):
#     test_name = 'test_ui_rpi_viz'
#     args = get_pipeline_args(suite='rpi_camera,visualize,ui')
#     rpi_device = is_rpi_camera_available()

#     if ('rpi' == detect_host_arch() and rpi_device):
#         log_file_path = os.path.join(log_dir, f"{pipeline['name']}_{test_name}_{run_method_name}.log")
        
#         if run_method_name == 'module':
#             stdout, stderr = run_methods[run_method_name](pipeline['module'], args, log_file_path)
#         elif run_method_name == 'pythonpath':
#             stdout, stderr = run_methods[run_method_name](pipeline['script'], args, log_file_path)
#         elif run_method_name == 'cli':
#             stdout, stderr = run_methods[run_method_name](pipeline['cli'], args, log_file_path)
#         else:
#             pytest.fail(f"Unknown run method: {run_method_name}")
        
#         out_str = stdout.decode().lower() if stdout else ""
#         err_str = stderr.decode().lower() if stderr else ""
#         print(f"Completed: {test_name}, {pipeline['name']}, {run_method_name}: {out_str}")
#         assert 'error' not in err_str, f"{pipeline['name']} ({run_method_name}) reported an error in {test_name}: {err_str}"
#         assert 'traceback' not in err_str, f"{pipeline['name']} ({run_method_name}) traceback in {test_name} : {err_str}"
#     else:
#         print('Not running on Raspberry Pi; skipping RPi camera run.')

@pytest.mark.parametrize('run_method_name', list(run_methods.keys()))
def test_cli_usb(pipeline, run_method_name):
    test_name = 'test_cli_usb'
    args = get_pipeline_args(suite='usb_camera')
    log_file_path = os.path.join(log_dir, f"{pipeline['name']}_{test_name}_{run_method_name}.log")
    
    if run_method_name == 'module':
        stdout, stderr = run_methods[run_method_name](pipeline['module'], args, log_file_path)
    elif run_method_name == 'pythonpath':
        stdout, stderr = run_methods[run_method_name](pipeline['script'], args, log_file_path)
    elif run_method_name == 'cli':
        stdout, stderr = run_methods[run_method_name](pipeline['cli'], args, log_file_path)
    else:
        pytest.fail(f"Unknown run method: {run_method_name}")
    
    out_str = stdout.decode().lower() if stdout else ""
    err_str = stderr.decode().lower() if stderr else ""
    print(f"Completed: {test_name}, {pipeline['name']}, {run_method_name}: {out_str}")
    assert 'error' not in err_str, f"{pipeline['name']} ({run_method_name}) reported an error in {test_name}: {err_str}"
    assert 'traceback' not in err_str, f"{pipeline['name']} ({run_method_name}) traceback in {test_name} : {err_str}"

@pytest.mark.parametrize('run_method_name', list(run_methods.keys()))
def test_ui_usb(pipeline, run_method_name):
    test_name = 'test_ui_usb'
    args = get_pipeline_args(suite='usb_camera,ui')
    log_file_path = os.path.join(log_dir, f"{pipeline['name']}_{test_name}_{run_method_name}.log")
    
    if run_method_name == 'module':
        stdout, stderr = run_methods[run_method_name](pipeline['module'], args, log_file_path)
    elif run_method_name == 'pythonpath':
        stdout, stderr = run_methods[run_method_name](pipeline['script'], args, log_file_path)
    elif run_method_name == 'cli':
        stdout, stderr = run_methods[run_method_name](pipeline['cli'], args, log_file_path)
    else:
        pytest.fail(f"Unknown run method: {run_method_name}")
    
    out_str = stdout.decode().lower() if stdout else ""
    err_str = stderr.decode().lower() if stderr else ""
    print(f"Completed: {test_name}, {pipeline['name']}, {run_method_name}: {out_str}")
    assert 'error' not in err_str, f"{pipeline['name']} ({run_method_name}) reported an error in {test_name}: {err_str}"
    assert 'traceback' not in err_str, f"{pipeline['name']} ({run_method_name}) traceback in {test_name} : {err_str}"

@pytest.mark.parametrize('run_method_name', list(run_methods.keys()))
def test_ui_clip(pipeline, run_method_name):
    test_name = 'test_ui_clip'
    args = get_pipeline_args(suite='ui')
    log_file_path = os.path.join(log_dir, f"{pipeline['name']}_{test_name}_{run_method_name}.log")
    
    if run_method_name == 'module':
        stdout, stderr = run_methods[run_method_name](pipeline['module'], args, log_file_path)
    elif run_method_name == 'pythonpath':
        stdout, stderr = run_methods[run_method_name](pipeline['script'], args, log_file_path)
    elif run_method_name == 'cli':
        stdout, stderr = run_methods[run_method_name](pipeline['cli'], args, log_file_path)
    else:
        pytest.fail(f"Unknown run method: {run_method_name}")
    
    out_str = stdout.decode().lower() if stdout else ""
    err_str = stderr.decode().lower() if stderr else ""
    print(f"Completed: {test_name}, {pipeline['name']}, {run_method_name}: {out_str}")
    assert 'error' not in err_str, f"{pipeline['name']} ({run_method_name}) reported an error in {test_name}: {err_str}"
    assert 'traceback' not in err_str, f"{pipeline['name']} ({run_method_name}) traceback in {test_name} : {err_str}"

@pytest.mark.parametrize('run_method_name', list(run_methods.keys()))
def test_delete(pipeline, run_method_name):
    test_name = 'test_delete'
    args = get_pipeline_args(suite='mode-delete') 
    log_file_path = os.path.join(log_dir, f"{pipeline['name']}_{test_name}_{run_method_name}.log")
    
    if run_method_name == 'module':
        stdout, stderr = run_methods[run_method_name](pipeline['module'], args, log_file_path)
    elif run_method_name == 'pythonpath':
        stdout, stderr = run_methods[run_method_name](pipeline['script'], args, log_file_path)
    elif run_method_name == 'cli':
        stdout, stderr = run_methods[run_method_name](pipeline['cli'], args, log_file_path)
    else:
        pytest.fail(f"Unknown run method: {run_method_name}")
    
    out_str = stdout.decode().lower() if stdout else ""
    err_str = stderr.decode().lower() if stderr else ""
    print(f"Completed: {test_name}, {pipeline['name']}, {run_method_name}: {out_str}")
    assert 'error' not in err_str, f"{pipeline['name']} ({run_method_name}) reported an error in {test_name}: {err_str}"
    assert 'traceback' not in err_str, f"{pipeline['name']} ({run_method_name}) traceback in {test_name} : {err_str}"

if __name__ == "__main__":
    pytest.main(["-v", __file__])