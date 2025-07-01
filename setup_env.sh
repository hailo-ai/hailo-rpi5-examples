#!/bin/bash
#
# This script configures the environment to allow running Python scripts
# from anywhere within the project, correctly resolving package imports.
# It will also activate the virtual environment.
#
# INSTRUCTIONS:
# 1. Run this script from the project's root directory using the 'source' command.
# 2. Example: source setup_env.sh
#
# After sourcing, your PYTHONPATH will be set for the current terminal session.

# Define virtual environment name
VENV_NAME="venv_hailo_rpi_examples"

# Function to check if the script is being sourced
is_sourced() {
    if [ -n "$ZSH_VERSION" ]; then
        [[ -o sourced ]]
    elif [ -n "$BASH_VERSION" ]; then
        [[ "${BASH_SOURCE[0]}" != "$0" ]]
    else
        echo "Unsupported shell. Please use bash or zsh."
        return 1
    fi
}

# Check kernel version
check_kernel_version() {
    # check if running on Raspberry Pi
    if uname -a | grep -q "Linux raspberrypi"; then

        # Check if CURRENT_VERSION is one of the invalid versions
        INVALID_KERNELS=("6.12.21" "6.12.22" "6.12.23" "6.12.24" "6.12.25")
        CURRENT_VERSION=$(uname -r | cut -d '+' -f 1) # Extract numeric version part

        if [[ " ${INVALID_KERNELS[@]} " =~ " ${CURRENT_VERSION} " ]]; then
            # If the current version is in the list of invalid versions, print an error message
            echo "Error: Kernel version $CURRENT_VERSION detected. This version is incompatible."
            echo "Please refer to the following link for more information:"
            echo "https://community.hailo.ai/t/raspberry-pi-kernel-compatibility-issue-temporary-fix/15322"
            return 1
        fi
    fi
}

# Only proceed if the script is being sourced
if is_sourced; then
    echo "Setting up the environment..."
    echo "Checking kernel version..."
    # Call the kernel version check function
    check_kernel_version || {
        echo "Exiting due to incompatible kernel version."
        return 1
    }
else
    echo "This script should be sourced, not executed directly."
    exit 1
fi

# Get the absolute path of the project's root directory (where this script is located).
PROJECT_ROOT=$(pwd)

# Prepend the project root to the PYTHONPATH.
# This ensures our project's modules are found first.
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

echo "Project directory added to PYTHONPATH for this session:"
echo "${PROJECT_ROOT}"

# Activate the virtual environment
if [ -d "$VENV_NAME" ]; then
    source $VENV_NAME/bin/activate
    echo "Virtual environment '$VENV_NAME' activated"
else
    echo "Virtual environment directory '$VENV_NAME' not found. Please ensure it is created and try again."
    return 1
fi