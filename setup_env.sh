#!/bin/bash

# Define the name of the virtual environment
VENV_NAME="venv_hailo_rpi5_examples"

# Function to check if the script is being sourced
is_sourced() {
    [[ "${BASH_SOURCE[0]}" != "$0" ]]
}

# Only proceed if the script is being sourced
if is_sourced; then
    echo "Setting up the environment..."
    TAPPAS_VERSION=$(pkg-config --modversion hailo-tappas-core)

    # Get the TAPPAS_VERSION
    TAPPAS_VERSION=$(echo $TAPPAS_VERSION)

    # Check if TAPPAS_VERSION is 3.28.1
    if [ "$TAPPAS_VERSION" == "3.28.1" ]; then
        echo "TAPPAS_VERSION is 3.28.1"
    else
        echo "TAPPAS_VERSION is not 3.28.1. Please ensure that TAPPAS_VERSION is set to 3.28.1."
    fi
    
    # Get the directory of the current script
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

    # Check if we are in the defined virtual environment
    if [[ "$VIRTUAL_ENV" == *"$VENV_NAME"* ]]; then
        echo "You are in the $VENV_NAME virtual environment."
    else
        echo "You are not in the $VENV_NAME virtual environment."

        # Check if the virtual environment exists in the same directory as the script
        if [ -d "$SCRIPT_DIR/$VENV_NAME" ]; then
            echo "Virtual environment exists. Activating..."
            source "$SCRIPT_DIR/$VENV_NAME/bin/activate"
        else
            echo "Virtual environment does not exist. Creating and activating..."
            python3 -m venv --system-site-packages "$SCRIPT_DIR/$VENV_NAME"
            source "$SCRIPT_DIR/$VENV_NAME/bin/activate"
        fi
    fi
            
    TAPPAS_POST_PROC_DIR=$(pkg-config --variable=tappas_postproc_lib_dir hailo-tappas-core)
    export TAPPAS_POST_PROC_DIR
    echo "TAAPAS_POST_PROC_DIR set to $TAPPAS_POST_PROC_DIR"

else
    echo "This script needs to be sourced to correctly set up the environment. Please run '. $(basename "$0")' instead of executing it."
fi
