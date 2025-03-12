#!/bin/bash

# Set the resource directory
RESOURCE_DIR="./resources"
mkdir -p "$RESOURCE_DIR"



# Define download function with file existence check and retries
download_model() {
  file_name=$(basename "$2")
  resource_dir="$1"

  if [ ! -f "$resource_dir/$file_name" ]; then
    echo "Downloading $file_name..."
    wget --tries=3 --retry-connrefused --quiet --show-progress "$2" -P "$resource_dir" || {
      echo "Failed to download $file_name after multiple attempts."
      # Instead of exit 1, log and continue
      echo "Download failed for $file_name. Continuing..."
    }
  else
    echo "File $file_name already exists. Skipping download."
  fi
}

# Define all URLs in arrays
GENERAL=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/chess/captured_image.jpg"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/chess/debug_detect_0.jpeg"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/chess/debug_detect_1.jpeg"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/chess/debug_detect_2.jpeg"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/chess/your_file.jpeg"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/chess/model.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/chess/Xception_last.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/chess/xception_preprocessed_pieces.npy"
)


# Run downloads for each array
for url in "${GENERAL[@]}"; do
  download_model "$RESOURCE_DIR" "$url" &
done

# Wait for all background downloads to complete
wait

echo "All downloads completed successfully!"
