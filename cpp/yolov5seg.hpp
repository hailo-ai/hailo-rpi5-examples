/**
 * Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
 * Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)
 **/
#pragma once
#include "hailo_objects.hpp"
#include "xtensor/xarray.hpp"
#include "xtensor/xio.hpp"

__BEGIN_DECLS
class Yolov5segParams
{
public:
    float iou_threshold;
    float score_threshold;
    int num_anchors;
    std::vector<int> outputs_size;
    std::vector<std::string> outputs_name;
    std::vector<xt::xarray<float>> anchors;
    std::vector<int> input_shape;
    std::vector<int> strides;
    std::vector<xt::xarray<float>> grids;
    std::vector<xt::xarray<float>> anchor_grids;

    Yolov5segParams() {
        iou_threshold = 0.6;
        score_threshold = 0.25;
        outputs_size = {20, 40, 80};
        outputs_name = {"yolov5n_seg/conv63", "yolov5n_seg/conv48", "yolov5n_seg/conv55", "yolov5n_seg/conv61"};
        anchors = {{116, 90, 156, 198, 373, 326},
                                            {30, 61, 62, 45, 59, 119},
                                            {10, 13, 16, 30, 33, 23} };
        input_shape = {640,640};
        strides = {32, 16, 8};
    }
};

Yolov5segParams *init(const std::string config_path, const std::string function_name);
void yolov5seg(HailoROIPtr roi, void *params_void_ptr);
void free_resources(void *params_void_ptr);
void filter(HailoROIPtr roi, void *params_void_ptr);
void filter_letterbox(HailoROIPtr roi, void *params_void_ptr);
__END_DECLS
