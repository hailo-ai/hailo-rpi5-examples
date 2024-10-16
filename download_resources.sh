#!/bin/bash

# Define download function
download_model() {
  wget -nc "$1" -P ./resources
}

# Define all URLs in an array
H8_HEFS=(
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov5m_wo_spp.hef"
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov8m_pose.hef"
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov5m_seg.hef"
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov6n.hef"
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov8s.hef"
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov8s_pose.hef"
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov5n_seg.hef"
  "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov8m_seg.hef"
)

H8L_HEFS=(
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov8s_h8l.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov5n_seg_h8l_mz.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov8s_pose_h8l_pi.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov6n.hef"
  "https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov8s-hailo8l-barcode.hef"
)

VIDEO_URL="https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/video/detection0.mp4"

# If --all flag is provided, download everything
if [ "$1" == "--all" ]; then
  echo "Downloading all models and video..."
  for url in "${H8_HEFS[@]}" "${H8L_HEFS[@]}"; do
    download_model "$url"
  done
  download_model "$VIDEO_URL"
else
  # Download only the default models from each category
  echo "Downloading the first three models from each category..."
  
  # Download first three H8 HEF models
  for i in {0..2}; do
    download_model "${H8_HEFS[i]}"
    download_model "${H8L_HEFS[i]}"
  done

  download_model "$VIDEO_URL"     # Download video
fi
