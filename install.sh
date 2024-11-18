#!/bin/bash

# Source environment variables and activate virtual environment
source setup_env.sh

# Install the required Python dependencies
pip install -r requirements.txt 

pip install -r tests/test_resources/requirements.txt

# Install additional system dependencies (if needed)
sudo apt install -y rapidjson-dev

# Check if the --all flag is provided
DOWNLOAD_RESOURCES_FLAG=""
if [[ "$1" == "--all" ]]; then
    DOWNLOAD_RESOURCES_FLAG="--all"
fi

# Download resources needed for the pipelines
./download_resources.sh $DOWNLOAD_RESOURCES_FLAG

# Optional: Post-process compilation (Only for older TAPPAS versions)
./compile_postprocess.sh