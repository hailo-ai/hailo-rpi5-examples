#!/bin/bash

# Set the resource directory
RESOURCE_DIR="./resources"
mkdir -p "$RESOURCE_DIR"

TRAIN_DIR="./resources/train"
mkdir -p "$TRAIN_DIR"

FACES_DIR="./resources/faces"
mkdir -p "$FACES_DIR"

# Define download function with file existence check and retries
download_model() {
  local url=$1
  local file_name=$(basename "$url")

  # Check if the file is for H8L and rename it accordingly
  if [[ "$url" == *"h8l_rpi"* && "$url" != *"_h8l.hef" ]]; then
    file_name="${file_name%.hef}_h8l.hef"
  fi

  local file_path="$RESOURCE_DIR/$file_name"

  if [ ! -f "$file_path" ]; then
    echo "Downloading $file_name..."
    wget -q --show-progress "$url" -O "$file_path" || {
      echo "Failed to download $file_name after multiple attempts."
      exit 1
    }
  else
    echo "File $file_name already exists in $RESOURCE_DIR. Skipping download."
  fi
}

# Define all URLs in arrays
H8_HEFS=(
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/scrfd_10g.hef"
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/arcface_mobilefacenet.hef"
)

H8L_HEFS=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/scrfd_2.5g.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/arcface_mobilefacenet_h8l.hef"
)

VIDEOS=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/video/face_recognition.mp4"
)

CONFIGS=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/configs/scrfd.json"
)

# If --all flag is provided, download everything in parallel
if [ "$1" == "--all" ]; then
  echo "Downloading all models and video resources..."
  for url in "${H8_HEFS[@]}" "${H8L_HEFS[@]}" "${VIDEOS[@]}"; do
    download_model "$url" &
  done
else
  if [ "$DEVICE_ARCHITECTURE" == "HAILO8L" ]; then
    echo "Downloading HAILO8L models..."
    for url in "${H8L_HEFS[@]}"; do
      download_model "$url" &
    done
  elif [ "$DEVICE_ARCHITECTURE" == "HAILO8" ]; then
    echo "Downloading HAILO8 models..."
    for url in "${H8_HEFS[@]}"; do
      download_model "$url" &
    done
  fi
fi

# Download additional videos
for url in "${VIDEOS[@]}" "${CONFIGS[@]}"; do
  download_model "$url" &
done

# Wait for all background downloads to complete
wait

echo "All downloads completed successfully!"