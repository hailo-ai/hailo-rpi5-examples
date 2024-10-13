#!/bin/bash

# download hef files to ./resources


# H8 HEFs
wget -nc https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov6n.hef -P ./resources
wget -nc https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov5m_wo_spp.hef -P ./resources
wget -nc https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov8s.hef -P ./resources
wget -nc https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov8s_pose.hef -P ./resources
wget -nc https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov8m_pose.hef -P ./resources
wget -nc https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov5n_seg.hef -P ./resources
wget -nc https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov5m_seg.hef -P ./resources
wget -nc https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov8m_seg.hef -P ./resources
wget -nc https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/ssd_mobilenet_v2.hef -P ./resources



# H8L HEFs
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov5n_seg_h8l_mz.hef -P ./resources
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov8s_pose_h8l_pi.hef -P ./resources
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov6n.hef -P ./resources
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov8s_h8l.hef -P ./resources
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov8s-hailo8l-barcode.hef -P ./resources
# download video file to ./resources
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/video/detection0.mp4 -P ./resources
