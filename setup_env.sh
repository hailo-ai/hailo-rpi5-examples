#!/bin/bash

# TAPPAS CORE Definitions
CORE_VENV_NAME="venv_hailo_rpi5_examples"
CORE_REQUIRED_VERSION=("3.30.0" "3.31.0")

# TAPPAS Definitions
TAPPAS_VENV_NAME="hailo_tappas_venv"
TAPPAS_REQUIRED_VERSION=("3.30.0" "3.31.0")

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

# Only proceed if the script is being sourced
if is_sourced; then
    echo "Setting up the environment..."

    # Check if we are working with hailo-tappas-core or hailo_tappas
    if pkg-config --exists hailo-tappas-core; then
        TAPPAS_CORE=1
        VENV_NAME=$CORE_VENV_NAME
        REQUIRED_VERSION=("${CORE_REQUIRED_VERSION[@]}")
        echo "Setting up the environment for hailo-tappas-core..."
        TAPPAS_VERSION=$(pkg-config --modversion hailo-tappas-core)
    else
        TAPPAS_CORE=0
        REQUIRED_VERSION=("${TAPPAS_REQUIRED_VERSION[@]}")
        echo "Setting up the environment for hailo_tappas..."
        TAPPAS_VERSION=$(pkg-config --modversion hailo_tappas)
        TAPPAS_WORKSPACE=$(pkg-config --variable=tappas_workspace hailo_tappas)
        export TAPPAS_WORKSPACE
        echo "TAPPAS_WORKSPACE set to $TAPPAS_WORKSPACE"
        if [[ "$TAPPAS_WORKSPACE" == "/local/workspace/tappas" ]]; then
            VENV_NAME="DOCKER"
        else
            VENV_NAME=$TAPPAS_VENV_NAME
        fi
    fi

    # Check if TAPPAS_VERSION is in REQUIRED_VERSION
    version_match=0
    for version in "${REQUIRED_VERSION[@]}"; do
        if [ "$TAPPAS_VERSION" = "$version" ]; then
            version_match=1
            break
        fi
    done

    if [ "$version_match" -eq 1 ]; then
        echo "TAPPAS_VERSION is ${TAPPAS_VERSION}. Proceeding..."
    else
        echo "TAPPAS_VERSION is ${TAPPAS_VERSION} not in the list of required versions ${REQUIRED_VERSION[*]}."
        return 1
    fi

    if [ $TAPPAS_CORE -eq 1 ]; then
        # Get the directory of the current script
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%N}}")" &> /dev/null && pwd)"
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
    else
        if [[ "$VENV_NAME" == "DOCKER" ]]; then
            echo "Running in DOCKER using default virtualenv"
        else
            # Check if we are in the defined virtual environment
            if [[ "$VIRTUAL_ENV" == *"$VENV_NAME"* ]]; then
                echo "You are in the $VENV_NAME virtual environment."
            else
                echo "You are not in the $VENV_NAME virtual environment."
                # Activate TAPPAS virtual environment
                VENV_PATH="${TAPPAS_WORKSPACE}/hailo_tappas_venv/bin/activate"
                if [ -f "$VENV_PATH" ]; then
                    echo "Activating virtual environment..."
                    source "$VENV_PATH"
                else
                    echo "Error: Virtual environment not found at $VENV_PATH."
                    return 1
                fi
            fi
        fi
        TAPPAS_POST_PROC_DIR="${TAPPAS_WORKSPACE}/apps/h8/gstreamer/libs/post_processes/"
    fi
    export TAPPAS_POST_PROC_DIR
    echo "TAPPAS_POST_PROC_DIR set to $TAPPAS_POST_PROC_DIR"

    # Get the Device Architecture
    output=$(hailortcli fw-control identify | tr -d '\0')
    # Extract the Device Architecture from the output
    device_arch=$(echo "$output" | grep "Device Architecture" | awk -F": " '{print $2}')
    # if the device architecture is not found, output the error message and return
    if [ -z "$device_arch" ]; then
        echo "Error: Device Architecture not found. Please check the connection to the device."
        return 1
    fi
    # Export the Device Architecture to an environment variable
    export DEVICE_ARCHITECTURE="$device_arch"
    # Print the environment variable to verify
    echo "DEVICE_ARCHITECTURE is set to: $DEVICE_ARCHITECTURE"
else
    echo "This script needs to be sourced to correctly set up the environment. Please run '. $(basename "$0")' instead of executing it."
fi