#!/bin/bash

# Function to check if the script is being sourced
is_sourced() {
    [[ "${BASH_SOURCE[0]}" != "$0" ]]
}

# Only proceed if the script is being sourced
if is_sourced; then
    echo "Setting up the environment..."

    # Fetch the workspace path using pkg-config
    TAPPAS_WORKSPACE=$(pkg-config --variable=tappas_workspace hailo_tappas)

    if [ -z "$TAPPAS_WORKSPACE" ]; then
        echo "Error: TAPPAS_WORKSPACE could not be determined."
        return 1 # Use 'return' instead of 'exit' to not exit the user's shell
    fi

    # Export the environment variable so it's available to subprocesses
    export TAPPAS_WORKSPACE
    echo "TAPPAS_WORKSPACE set to $TAPPAS_WORKSPACE"

    # Activate the virtual environment
    VENV_PATH="${TAPPAS_WORKSPACE}/hailo_tappas_venv/bin/activate"
    if [ -f "$VENV_PATH" ]; then
        echo "Activating virtual environment..."
        source "$VENV_PATH"
    else
        echo "Error: Virtual environment not found at $VENV_PATH."
        return 1
    fi
else
    echo "This script needs to be sourced to correctly set up the environment. Please run '. $(basename "$0")' instead of executing it."
fi
