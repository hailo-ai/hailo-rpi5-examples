#!/bin/bash

# Script to download all files from a Google Drive folder
# The folder is hardcoded in this script

# Check for required tool: gdown
check_tools() {
    if ! command -v gdown &>/dev/null; then
        echo "Error: 'gdown' is not installed."
        echo "Install it using 'pip install gdown'."
        exit 1
    fi
}

# Download the entire folder
download_folder() {
    echo "Downloading folder from Google Drive..."
    # Hardcoded folder link
    FOLDER_LINK="https://drive.google.com/drive/folders/1l4IWCEeaECMRHrkUgjaimioue_bNovrJ"
    # Use gdown to download the folder
    gdown --folder "$FOLDER_LINK" --output "./TEMPO_FILES"

    if [[ $? -eq 0 ]]; then
        echo "Download completed successfully. Files saved in './TEMPO_FILES'."
    else
        echo "Error: Failed to download files."
    fi
}

# Main script execution
check_tools
download_folder
