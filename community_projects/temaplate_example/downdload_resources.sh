#!/bin/bash

# Instructions:
# 1. This script downloads the specified file from the Hailo Model Zoo.
# 2. The file will be saved into the 'resources' directory.
# 3. Ensure 'wget' is installed on your system.

# URL of the file to download
FILE_URL="https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov5m_wo_spp.hef"

# Create resources directory if it doesn't exist
mkdir -p ./resources

# Function to download the file
download_file() {
    URL=$1
    FILENAME=$(basename "$URL")
    OUTPUT_FILE="./resources/$FILENAME"

    echo "Downloading: $FILENAME"

    # Download the file
    wget --quiet --show-progress --no-clobber --directory-prefix=./resources "$URL" || {
        echo "Error downloading: $URL"
        return 1
    }

    echo "Successfully downloaded: $FILENAME"
}

# Main logic
echo "Starting download..."

# Download the specified file
download_file "$FILE_URL"

echo "Download completed."
