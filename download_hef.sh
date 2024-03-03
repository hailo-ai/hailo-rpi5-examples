#!/bin/bash

# download hef files to ./resources

wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.10.0/hailo8/yolov5n_seg.hef -P ./resources
wget https://hailo-tappas.s3.eu-west-2.amazonaws.com/v3.26/general/hefs/yolov5m_wo_spp_60p.hef -P ./resources
wget https://hailo-tappas.s3.eu-west-2.amazonaws.com/v3.26/general/hefs/centerpose_regnetx_1.6gf_fpn.hef -P ./resources

