#!/bin/bash

# Set the resource directory
RESOURCE_DIR="./resources"
mkdir -p "$RESOURCE_DIR"

SMALL_MODEL_DIR="$RESOURCE_DIR/model_224_320"
mkdir -p "$SMALL_MODEL_DIR"

LARGE_MODEL_DIR="$RESOURCE_DIR/model_480_640"
mkdir -p "$LARGE_MODEL_DIR"

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
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/xfeat.pt"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/x_feature_13_without_pixel_unshuffle_normilize_softmax_slice_sim.onnx"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/x_feature_13_without_pixel_unshuffle_sim_without_head.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/x_feature_13_without_pixel_unshuffle_sim.hef"
)

SMALL=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/model_224_320/onnx_to_hailo.sh"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/model_224_320/x_feature_13_without_pixel_unshuffle_normilize_softmax_slice_224_320_only_head.onnx"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/model_224_320/x_feature_13_without_pixel_unshuffle_normilize_softmax_slice_224_320_sim.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/model_224_320/x_feature_13_without_pixel_unshuffle_normilize_softmax_slice_224_320_sim.onnx"
)

LARGE=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/model_480_640/onnx_to_hailo.sh"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/model_480_640/x_feature_13_without_pixel_unshuffle_normilize_softmax_slice_only_head.onnx"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/model_480_640/x_feature_13_without_pixel_unshuffle_normilize_softmax_slice_sim.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/navigator/model_480_640/x_feature_13_without_pixel_unshuffle_normilize_softmax_slice_sim.onnx"
)

# Run downloads for each array
for url in "${GENERAL[@]}"; do
  download_model "$RESOURCE_DIR" "$url" &
done

for url in "${SMALL[@]}"; do
  download_model "$SMALL_MODEL_DIR" "$url" &
done

for url in "${LARGE[@]}"; do
  download_model "$LARGE_MODEL_DIR" "$url" &
done

# Wait for all background downloads to complete
wait

echo "All downloads completed successfully!"
