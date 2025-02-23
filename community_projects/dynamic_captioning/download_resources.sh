#!/bin/bash

# Set the resource directory
RESOURCE_DIR="./resources"
mkdir -p "$RESOURCE_DIR"

EMBEDDINGS_DIR="$RESOURCE_DIR/embeddings"
mkdir -p "$EMBEDDINGS_DIR"

MODELS_DIR="$RESOURCE_DIR/models"
mkdir -p "$MODELS_DIR"

TOKENIZER_DIR="$RESOURCE_DIR/tokenizer"
mkdir -p "$TOKENIZER_DIR"

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
EMBEDDINGS=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/dynamic_captioning/caption_embedding.npy"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/dynamic_captioning/word_embedding.npy"
)

MODELS=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/dynamic_captioning/florence2_transformer_decoder.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/dynamic_captioning/florence2_transformer_encoder.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/dynamic_captioning/vision_encoder.onnx"
  )

TOKENIZER=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hackathon/dynamic_captioning/tokenizer.json"
)

# Run downloads for each array
for url in "${EMBEDDINGS[@]}"; do
  download_model "$EMBEDDINGS_DIR" "$url" &
done

for url in "${MODELS[@]}"; do
  download_model "$MODELS_DIR" "$url" &
done

for url in "${TOKENIZER[@]}"; do
  download_model "$TOKENIZER_DIR" "$url" &
done

# Wait for all background downloads to complete
wait

echo "All downloads completed successfully!"