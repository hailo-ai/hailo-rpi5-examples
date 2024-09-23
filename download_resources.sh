#!/bin/bash

# download hef files to ./resources


# H8 HEFs
# wget -nc https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.10.0/hailo8/yolov5n_seg.hef -P ./resources
# wget -nc https://hailo-tappas.s3.eu-west-2.amazonaws.com/v3.26/general/hefs/yolov5m_wo_spp_60p.hef -P ./resources
# wget -nc https://hailo-tappas.s3.eu-west-2.amazonaws.com/v3.26/general/hefs/centerpose_regnetx_1.6gf_fpn.hef -P ./resources

# H8L HEFs
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov5n_seg_h8l_mz.hef -P ./resources
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov8s_pose_h8l_pi.hef -P ./resources
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov6n.hef -P ./resources
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov8s_h8l.hef -P ./resources
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/hefs/h8l_rpi/yolov8s-hailo8l-barcode.hef -P ./resources
# download video file to ./resources
wget -nc https://hailo-csdata.s3.eu-west-2.amazonaws.com/resources/video/detection0.mp4 -P ./resources
