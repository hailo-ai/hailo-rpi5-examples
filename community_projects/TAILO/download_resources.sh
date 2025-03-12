#!/bin/bash

# Instructions:
# 1. This script downloads specified files from the Hailo Model Zoo.
# 2. The files will be saved into the 'resources' directory.
# 3. Ensure 'wget' is installed on your system.

# Array of file URLs to download
FILE_URLS=(
    "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/tailo/warn_pet1.mp3"
    "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/tailo/warn_pet2.mp3"
    "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/tailo/warn_pet3.mp3"
    "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/tailo/treat_pet1.mp3"
    "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/tailo/brandy_on_couch.mp4"

)

# Create resources directory if it doesn't exist
mkdir -p ./resources

# Function to download a file
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
echo "Starting downloads..."

# Iterate over the list of URLs and download each
for URL in "${FILE_URLS[@]}"; do
    download_file "$URL"
done

echo "Clone Dynamixel SDK"
mkdir -p ./open_source
pushd "open_source"
git clone https://github.com/ROBOTIS-GIT/DynamixelSDK.git
pushd "DynamixelSDK/python"
sudo python setup.py install
popd
popd


echo "All downloads completed."
