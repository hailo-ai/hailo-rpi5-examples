#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Install the required Python dependencies
echo "Installing required Python dependencies..."
pip install -r requirements.txt

# Download resources needed for the pipelines
echo "Downloading resources needed for the pipelines..."
./download_resources.sh $DOWNLOAD_RESOURCES_FLAG

# Compiling C++ code
echo "Compiling C++ code..."
./compile_postprocess.sh

echo "Installation completed successfully."