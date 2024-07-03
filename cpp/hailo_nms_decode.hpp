/**
 * Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
 * Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)
 **/
#include <vector>
#include <string>
#include <iostream>
#include <cstring>
#include "hailo/hailort.h"
#include "hailo_objects.hpp"
#include "common/structures.hpp"
#include "common/nms.hpp"
#include "common/labels/coco_ninety.hpp"
#include "common/labels/coco_visdrone.hpp"

static const int DEFAULT_MAX_BOXES = 100;
static const float DEFAULT_THRESHOLD = 0.4;

class HailoNMSDecode
{
private:
    HailoTensorPtr _nms_output_tensor;
    std::map<uint8_t, std::string> labels_dict;
    float _detection_thr;
    uint _max_boxes;
    bool _filter_by_score;
    const hailo_vstream_info_t _vstream_info;

    common::hailo_bbox_float32_t dequantize_hailo_bbox(const auto *bbox_struct)
    {
        // Dequantization of common::hailo_bbox_t (uint16_t) to common::hailo_bbox_float32_t (float32_t)
        common::hailo_bbox_float32_t dequant_bbox = {
            .y_min = _nms_output_tensor->fix_scale(bbox_struct->y_min),
            .x_min = _nms_output_tensor->fix_scale(bbox_struct->x_min),
            .y_max = _nms_output_tensor->fix_scale(bbox_struct->y_max),
            .x_max = _nms_output_tensor->fix_scale(bbox_struct->x_max),
            .score = _nms_output_tensor->fix_scale(bbox_struct->score)};

        return dequant_bbox;
    }

    void parse_bbox_to_detection_object(auto dequant_bbox, uint32_t class_index, std::vector<HailoDetection> &_objects)
    {
        float confidence = CLAMP(dequant_bbox.score, 0.0f, 1.0f);
        // filter score by detection threshold if needed.
        if (!_filter_by_score || dequant_bbox.score > _detection_thr)
        {
            float32_t w, h = 0.0f;
            // parse width and height of the box
            std::tie(w, h) = get_shape(&dequant_bbox);
            // create new detection object and add it to the vector of detections
            _objects.push_back(HailoDetection(HailoBBox(dequant_bbox.x_min, dequant_bbox.y_min, w, h), class_index, labels_dict[class_index], confidence));
        }
    }
    
    std::pair<float, float> get_shape(auto *bbox_struct)
    {
        float32_t w = bbox_struct->x_max - bbox_struct->x_min;
        float32_t h = bbox_struct->y_max - bbox_struct->y_min;
        return std::pair<float, float>(w, h);
    }

public:
    HailoNMSDecode(HailoTensorPtr tensor, std::map<uint8_t, std::string> &labels_dict, float detection_thr = DEFAULT_THRESHOLD, uint max_boxes = DEFAULT_MAX_BOXES, bool filter_by_score = false)
        : _nms_output_tensor(tensor), labels_dict(labels_dict), _detection_thr(detection_thr), _max_boxes(max_boxes), _filter_by_score(filter_by_score), _vstream_info(tensor->vstream_info())
    {
        // making sure that the network's output is indeed an NMS type, by checking the order type value included in the metadata
        if (HAILO_FORMAT_ORDER_HAILO_NMS != _vstream_info.format.order)
            throw std::invalid_argument("Output tensor " + _nms_output_tensor->name() + " is not an NMS type");
    };

    template <typename T, typename BBoxType>
    std::vector<HailoDetection> decode()
    {
        /*
        NMS output decode method
        ------------------------

        decodes the nms buffer received from the output tensor of the network.
        returns a vector of DetectonObject filtered by the detection threshold.

        The data is sorted by the number of the classes.
        for each class - first comes the number of boxes in the class, then the boxes one after the other,
        each box contains x_min, y_min, x_max, y_max and score (uint16_t\float32 each) and can be casted to common::hailo_bbox_t struct (5*uint16_t).
        means that a frame size of one class is sizeof(bbox_count) + bbox_count * sizeof(common::hailo_bbox_t).
        and the actual size of the data is (frame size of one class)*number of classes.

        If the data comes after quantization - so dequantization to float32 is needed.

        As an example - quantized data buffer of a frame that contains a person and two dogs:
        (person class id = 1, dog class id = 18)

        1 107 96 143 119 172 0 0 0 0 0 0 0 0 0 0 0 0 0
        0 0 2 123 124 140 150 92 112 125 138 147 91 0 0
        0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
        0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
        0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0

        taking the dogs as example - 2 123 124 140 150 92 112 125 138 147 91
        can be split to two different boxes
        common::hailo_bbox_t st_1 = 123 124 140 150 92
        common::hailo_bbox_t st_2 = 112 125 138 147 91
        now after dequntization of st_1 - we get common::hailo_bbox_float32_t:
        ymin = 0.551805 xmin = 0.389635 ymax = 0.741805 xmax = 0.561974 score = 0.95
        */

        if (!_nms_output_tensor)
            return std::vector<HailoDetection>{};

        std::vector<HailoDetection> _objects;
        _objects.reserve(_max_boxes);
        uint32_t max_bboxes_per_class = _vstream_info.nms_shape.max_bboxes_per_class;
        uint32_t num_of_classes = _vstream_info.nms_shape.number_of_classes;
        size_t buffer_offset = 0;
        uint8_t *buffer = _nms_output_tensor->data();
        for (size_t class_id = 0; class_id < num_of_classes; class_id++)
        {
            float32_t bbox_count = 0;
            memcpy(&bbox_count, buffer + buffer_offset, sizeof(bbox_count));
            buffer_offset += sizeof(bbox_count);

            if (bbox_count == 0) // No detections
                continue;
            if (bbox_count > max_bboxes_per_class)
                throw std::runtime_error("Runtime error - Got more than the maximum bboxes per class in the nms buffer");

            for (size_t bbox_index = 0; bbox_index < static_cast<uint32_t>(bbox_count); bbox_index++)
            {
                if (std::is_same<T, uint16_t>::value)
                {
                    // output type (T) is uint16, so we need to do dequantization before parsing
                    hailo_bbox_float32_t *bbox = (hailo_bbox_float32_t *)(&buffer[buffer_offset]);
                    parse_bbox_to_detection_object(*bbox, class_id + 1, _objects);
                    buffer_offset += sizeof(hailo_bbox_float32_t);
                }
                else
                {
                    BBoxType *bbox_struct = (BBoxType *)(&buffer[buffer_offset]);
                    parse_bbox_to_detection_object(*bbox_struct, class_id + 1, _objects);
                    buffer_offset += sizeof(BBoxType);
                }
            }
        }
        return _objects;
    }
};
