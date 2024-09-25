#!/bin/bash

# Ensure the repository is cloned and you're in the correct directory
# Uncomment if you haven't cloned it yet
#git clone https://github.com/hailo-ai/hailo-rpi5-examples.git

# Enter the repository directory
#cd hailo-rpi5-examples || exit

# Source environment variables and activate virtual environment
source setup_env.sh

# Install the required Python dependencies
pip install -r requirements.txt

# Install additional system dependencies (if needed)
sudo apt install -y rapidjson-dev

# Download resources needed for the pipelines
./download_resources.sh

# Optional: Post-process compilation (Only for older TAPPAS versions)
./compile_postprocess.sh


# Activate the virtual environment to Run the examples 
. venv_hailo_rpi5_examples/bin/activate

# Re run the source setup_env.sh
source setup_env.sh

# Run the Classification pipeline example
#python3 examples/classification.py

# Run the Object Detection pipeline example
#python3 examples/object_detection.py

# Run other examples here as needed
# python3 examples/human_pose_estimation.py
# python3 examples/instance_segmentation.py

