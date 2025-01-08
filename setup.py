from setuptools import setup, find_packages
import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_hailo_package():
    """Verify if Hailo package is installed."""
    try:
        import hailo
    except ImportError:
        logger.error("Hailo package not found. Please activate the virtual environment and try again.")
        sys.exit(1)

def read_requirements():
    """Read and parse requirements.txt, converting Git-based dependencies."""
    with open("requirements.txt", "r") as f:
        lines = f.read().splitlines()

    parsed_lines = []
    for line in lines:
        if line.startswith("git+https://"):
            # Extract the package name for PEP 508 syntax
            package_name = line.split("/")[-1].split(".")[0]
            parsed_lines.append(f"{package_name} @ {line}")
        else:
            parsed_lines.append(line)
    return parsed_lines

def run_shell_command(command, error_message):
    """Run shell commands and handle errors."""
    logger.info(f"Running command: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        logger.error(f"{error_message}. Exit code: {result.returncode}")
        sys.exit(result.returncode)

def get_downloaded_files():
    """Get a list of downloaded files from the resources directory."""
    resource_dir = os.path.join(os.path.dirname(__file__), 'resources')
    downloaded_files = []
    for root, _, files in os.walk(resource_dir):
        for file in files:
            relative_path = os.path.relpath(os.path.join(root, file), 'resources')
            downloaded_files.append(relative_path)
    return downloaded_files

def main():
    check_hailo_package()

    logger.info("Reading requirements...")
    requirements = read_requirements()

    logger.info("Compiling C++ code...")
    run_shell_command("./compile_postprocess.sh", "Failed to compile C++ code")

    logger.info("Downloading resources...")
    run_shell_command("./download_resources.sh --all", "Failed to download resources")

    setup(
        name='hailo_apps_infra',
        version='0.2.0',
        description='A collection of infrastructure utilities for Hailo applications',
        long_description=open('README.md').read(),
        long_description_content_type='text/markdown',
        author='Hailo',
        author_email='support@hailo.ai',
        url='https://github.com/hailo-ai/hailo-apps-infra',
        install_requires=requirements,
        packages=find_packages(exclude=["tests", "docs"]),
        package_data={
            'hailo_apps_infra': ['*.json', '*.sh', '*.cpp', '*.hpp', '*.pc'] + get_downloaded_files(),
        },
        include_package_data=True,
        entry_points={
            'console_scripts': [
                'get-usb-camera=hailo_apps_infra.get_usb_camera:main'
            ],
        },
    )

if __name__ == '__main__':
    main()
