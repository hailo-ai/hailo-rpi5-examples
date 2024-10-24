/**
 * Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
 * Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)
 **/
// General includes
#include <iostream>
#include <vector>

// Hailo includes
#include "hailo_xtensor.hpp"
#include "common/math.hpp"
#include "common/tensors.hpp"
#include "common/labels/coco_eighty.hpp"
#include "yolov8pose_postprocess.hpp"

#include "xtensor/xadapt.hpp"
#include "xtensor/xarray.hpp"
#include "xtensor/xcontainer.hpp"
#include "xtensor/xeval.hpp"
#include "xtensor/xtensor.hpp"
#include "xtensor/xindex_view.hpp"
#include "xtensor/xio.hpp"
#include "xtensor/xmanipulation.hpp"
#include "xtensor/xmasked_view.hpp"
#include "xtensor/xoperation.hpp"
#include "xtensor/xpad.hpp"
#include "xtensor/xrandom.hpp"
#include "xtensor/xshape.hpp"
#include "xtensor/xsort.hpp"
#include "xtensor/xstrided_view.hpp"
#include "xtensor/xview.hpp"

using namespace xt::placeholders;

#define SCORE_THRESHOLD 0.6
#define IOU_THRESHOLD 0.7
#define NUM_CLASSES 1

std::vector<std::pair<int, int>> JOINT_PAIRS = {
    {0, 1}, {1, 3}, {0, 2}, {2, 4}, {5, 6}, {5, 7}, {7, 9}, {6, 8}, {8, 10}, {5, 11}, {6, 12}, {11, 12}, {11, 13}, {12, 14}, {13, 15}, {14, 16}};

std::pair<std::vector<KeyPt>, std::vector<PairPairs>> process_single_decoding(const Decodings &dec, const std::vector<int> &network_dims, float joint_threshold = 0.5)
{
    std::vector<KeyPt> keypoints;
    std::vector<PairPairs> pairs;

    auto keypoint_coordinates_and_score = dec.keypoints;
    auto coordinates = keypoint_coordinates_and_score.first;
    auto score = keypoint_coordinates_and_score.second;

    // Filter keypoints
    for (uint i = 0; i < score.shape(0); i++)
    {
        if (score(i, 0) > joint_threshold)
        {
            keypoints.push_back(KeyPt({coordinates(i, 0) / network_dims[0], coordinates(i, 1) / network_dims[1], score(i, 0)}));
        }
    }

    // Filter joints pair
    for (const auto &pair : JOINT_PAIRS)
    {
        if (score(pair.first, 0) >= joint_threshold && score(pair.second, 0) >= joint_threshold)
        {
            PairPairs pr = PairPairs({std::make_pair(coordinates(pair.first, 0) / network_dims[0], coordinates(pair.first, 1) / network_dims[1]),
                                      std::make_pair(coordinates(pair.second, 0) / network_dims[0], coordinates(pair.second, 1) / network_dims[1]),
                                      score(pair.first, 0),
                                      score(pair.second, 0)});
            pairs.push_back(pr);
        }
    }
    return std::make_pair(keypoints, pairs);
}

// filter keypoints iterates over all decodings
std::pair<std::vector<KeyPt>, std::vector<PairPairs>> filter_keypoints(const std::vector<Decodings> &filtered_decodings, const std::vector<int> &network_dims, float joint_threshold = 0.5)
{
    std::vector<KeyPt> filtered_keypoints;
    std::vector<PairPairs> filtered_pairs;

    for (const auto &dec : filtered_decodings)
    {
        auto result = process_single_decoding(dec, network_dims, joint_threshold);
        filtered_keypoints.insert(filtered_keypoints.end(), result.first.begin(), result.first.end());
        filtered_pairs.insert(filtered_pairs.end(), result.second.begin(), result.second.end());
    }

    return std::make_pair(filtered_keypoints, filtered_pairs);
}

float iou_calc(const HailoBBox &box_1, const HailoBBox &box_2)
{
    // Calculate IOU between two detection boxes
    const float width_of_overlap_area = std::min(box_1.xmax(), box_2.xmax()) - std::max(box_1.xmin(), box_2.xmin());
    const float height_of_overlap_area = std::min(box_1.ymax(), box_2.ymax()) - std::max(box_1.ymin(), box_2.ymin());
    const float positive_width_of_overlap_area = std::max(width_of_overlap_area, 0.0f);
    const float positive_height_of_overlap_area = std::max(height_of_overlap_area, 0.0f);
    const float area_of_overlap = positive_width_of_overlap_area * positive_height_of_overlap_area;
    const float box_1_area = (box_1.ymax() - box_1.ymin()) * (box_1.xmax() - box_1.xmin());
    const float box_2_area = (box_2.ymax() - box_2.ymin()) * (box_2.xmax() - box_2.xmin());
    // The IOU is a ratio of how much the boxes overlap vs their size outside the overlap.
    // Boxes that are similar will have a higher overlap threshold.
    return area_of_overlap / (box_1_area + box_2_area - area_of_overlap);
}

std::vector<Decodings> nms(std::vector<Decodings> &decodings, const float iou_thr, bool should_nms_cross_classes = false)
{

    std::vector<Decodings> decodings_after_nms;

    for (uint index = 0; index < decodings.size(); index++)
    {
        if (decodings[index].detection_box.get_confidence() != 0.0f)
        {
            for (uint jindex = index + 1; jindex < decodings.size(); jindex++)
            {
                if ((should_nms_cross_classes || (decodings[index].detection_box.get_class_id() == decodings[jindex].detection_box.get_class_id())) &&
                    decodings[jindex].detection_box.get_confidence() != 0.0f)
                {
                    // For each detection, calculate the IOU against each following detection.
                    float iou = iou_calc(decodings[index].detection_box.get_bbox(), decodings[jindex].detection_box.get_bbox());
                    // If the IOU is above threshold, then we have two similar detections,
                    // and want to delete the one.
                    if (iou >= iou_thr)
                    {
                        // The detections are arranged in highest score order,
                        // so we want to erase the latter detection.
                        decodings[jindex].detection_box.set_confidence(0.0f);
                    }
                }
            }
        }
    }
    for (uint index = 0; index < decodings.size(); index++)
    {
        if (decodings[index].detection_box.get_confidence() != 0.0f)
        {
            decodings_after_nms.push_back(Decodings{decodings[index].detection_box, decodings[index].keypoints, decodings[index].joint_pairs});
        }
    }
    return decodings_after_nms;
}

float dequantize_value(uint16_t val, float32_t qp_scale, float32_t qp_zp)
{
    return (float(val) - qp_zp) * qp_scale;
}

void dequantize_box_values(xt::xarray<float> &dequantized_outputs, int index,
                           xt::xarray<uint16_t> &quantized_outputs,
                           size_t dim1, size_t dim2, float32_t qp_scale, float32_t qp_zp)
{
    for (size_t i = 0; i < dim1; i++)
    {
        for (size_t j = 0; j < dim2; j++)
        {
            dequantized_outputs(i, j) = dequantize_value(quantized_outputs(index, i, j), qp_scale, qp_zp);
        }
    }
}

std::vector<xt::xarray<double>> get_centers(std::vector<int> &strides, std::vector<int> &network_dims,
                                            std::size_t boxes_num, int strided_width, int strided_height)
{

    std::vector<xt::xarray<double>> centers(boxes_num);

    for (uint i = 0; i < boxes_num; i++)
    {
        strided_width = network_dims[0] / strides[i];
        strided_height = network_dims[1] / strides[i];

        // Create a meshgrid of the proper strides
        xt::xarray<int> grid_x = xt::arange(0, strided_width);
        xt::xarray<int> grid_y = xt::arange(0, strided_height);

        auto mesh = xt::meshgrid(grid_x, grid_y);
        grid_x = std::get<1>(mesh);
        grid_y = std::get<0>(mesh);

        // Use the meshgrid to build up box center prototypes
        auto ct_row = (xt::flatten(grid_y) + 0.5) * strides[i];
        auto ct_col = (xt::flatten(grid_x) + 0.5) * strides[i];

        centers[i] = xt::stack(xt::xtuple(ct_col, ct_row, ct_col, ct_row), 1);
    }

    return centers;
}

std::vector<Decodings> decode_boxes_and_keypoints(std::vector<HailoTensorPtr> raw_boxes_outputs,
                                                  xt::xarray<float> scores,
                                                  std::vector<HailoTensorPtr> raw_keypoints,
                                                  std::vector<int> network_dims,
                                                  std::vector<int> strides,
                                                  int regression_length)
{
    int strided_width = -1;
    int strided_height = -1;
    int class_index = 0;
    std::vector<Decodings> decodings;
    std::vector<PairPairs> joint_pairs;
    int instance_index = 0;
    float confidence = 0.0;
    std::string label;

    auto centers = get_centers(std::ref(strides), std::ref(network_dims), raw_boxes_outputs.size(), strided_width, strided_height);

    // Box distribution to distance
    auto regression_distance = xt::reshape_view(xt::arange(0, regression_length + 1), {1, 1, regression_length + 1});

    for (uint i = 0; i < raw_boxes_outputs.size(); i++)
    {
        // Boxes setup
        float32_t qp_scale = raw_boxes_outputs[i]->vstream_info().quant_info.qp_scale;
        float32_t qp_zp = raw_boxes_outputs[i]->vstream_info().quant_info.qp_zp;

        auto output_b = common::get_xtensor(raw_boxes_outputs[i]);
        int num_proposals = output_b.shape(0) * output_b.shape(1);
        auto output_boxes = xt::view(output_b, xt::all(), xt::all(), xt::all());
        xt::xarray<uint16_t> quantized_boxes = xt::reshape_view(output_boxes, {num_proposals, 4, regression_length + 1});

        auto shape = {quantized_boxes.shape(1), quantized_boxes.shape(2)};

        // Keypoints setup
        float32_t qp_scale_kpts = raw_keypoints[i]->vstream_info().quant_info.qp_scale;
        float32_t qp_zp_kpts = raw_keypoints[i]->vstream_info().quant_info.qp_zp;
        hailo_format_type_t keypoints_format = raw_keypoints[i]->vstream_info().format.type;
        if (keypoints_format == HAILO_FORMAT_TYPE_UINT8)
        {
            throw std::runtime_error("This postprocess does not support uint8 keypoints format, download the updated HEF version.");
        }

        auto output_keypoints = common::get_xtensor_uint16(raw_keypoints[i]);
        int num_proposals_keypoints = output_keypoints.shape(0) * output_keypoints.shape(1);
        auto output_keypoints_quantized = xt::view(output_keypoints, xt::all(), xt::all(), xt::all());
        xt::xarray<uint16_t> quantized_keypoints = xt::reshape_view(output_keypoints_quantized, {num_proposals_keypoints, 17, 3});

        auto keypoints_shape = {quantized_keypoints.shape(1), quantized_keypoints.shape(2)};

        // Bbox decoding
        for (uint j = 0; j < uint(num_proposals); j++)
        {
            confidence = xt::row(scores, instance_index)(0);
            instance_index++;
            if (confidence < SCORE_THRESHOLD)
                continue;

            xt::xarray<float> box(shape);
            xt::xarray<float> kpts_corrdinates_and_scores(keypoints_shape);

            dequantize_box_values(box, j, quantized_boxes,
                                  box.shape(0), box.shape(1),
                                  qp_scale, qp_zp);
            common::softmax_2D(box.data(), box.shape(0), box.shape(1));

            auto box_distance = box * regression_distance;
            xt::xarray<float> reduced_distances = xt::sum(box_distance, {2});
            auto strided_distances = reduced_distances * strides[i];

            // Decode box
            auto distance_view1 = xt::view(strided_distances, xt::all(), xt::range(_, 2)) * -1;
            auto distance_view2 = xt::view(strided_distances, xt::all(), xt::range(2, _));
            auto distance_view = xt::concatenate(xt::xtuple(distance_view1, distance_view2), 1);
            auto decoded_box = centers[i] + distance_view;

            HailoBBox bbox(decoded_box(j, 0) / network_dims[0],
                           decoded_box(j, 1) / network_dims[1],
                           (decoded_box(j, 2) - decoded_box(j, 0)) / network_dims[0],
                           (decoded_box(j, 3) - decoded_box(j, 1)) / network_dims[1]);

            label = common::coco_eighty[class_index + 1];
            HailoDetection detected_instance(bbox, class_index, label, confidence);

            // Decode keypoints
            dequantize_box_values(kpts_corrdinates_and_scores, j, quantized_keypoints,
                                  kpts_corrdinates_and_scores.shape(0), kpts_corrdinates_and_scores.shape(1),
                                  qp_scale_kpts, qp_zp_kpts);

            auto kpts_corrdinates = xt::view(kpts_corrdinates_and_scores, xt::all(), xt::range(0, 2));
            auto keypoints_scores = xt::view(kpts_corrdinates_and_scores, xt::all(), xt::range(2, xt::placeholders::_));

            kpts_corrdinates *= 2;

            auto center = xt::view(centers[i], xt::all(), xt::range(0, 2));
            auto center_values = xt::xarray<float>{(float)center(j, 0), (float)center(j, 1)};

            kpts_corrdinates = strides[i] * (kpts_corrdinates - 0.5) + center_values;

            // Apply sigmoid to keypoints scores
            auto sigmoided_scores = 1 / (1 + xt::exp(-keypoints_scores));

            auto keypoint = std::make_pair(kpts_corrdinates, sigmoided_scores);

            decodings.push_back(Decodings{detected_instance, keypoint, joint_pairs});
        }
    }

    return decodings;
}

Triple get_boxes_scores_keypoints(std::vector<HailoTensorPtr> &tensors, int num_classes, int regression_length)
{
    std::vector<HailoTensorPtr> outputs_boxes(tensors.size() / 3);
    std::vector<HailoTensorPtr> outputs_keypoints(tensors.size() / 3);

    // Prepare the scores xarray at the size we will fill in in-place
    int total_scores = 0;
    for (uint i = 0; i < tensors.size(); i = i + 3)
    {
        total_scores += tensors[i + 1]->width() * tensors[i + 1]->height();
    }

    std::vector<size_t> scores_shape = {(long unsigned int)total_scores, (long unsigned int)num_classes};

    xt::xarray<float> scores(scores_shape);

    int view_index_scores = 0;

    for (uint i = 0; i < tensors.size(); i = i + 3)
    {
        // Bounding boxes extraction will be done later on only on the boxes that surpass the score threshold
        outputs_boxes[i / 3] = tensors[i];

        // Extract and dequantize the scores outputs
        auto dequantized_output_s = common::dequantize(common::get_xtensor(tensors[i + 1]), tensors[i + 1]->vstream_info().quant_info.qp_scale, tensors[i + 1]->vstream_info().quant_info.qp_zp);
        int num_proposals_scores = dequantized_output_s.shape(0) * dequantized_output_s.shape(1);

        // From the layer extract the scores
        auto output_scores = xt::view(dequantized_output_s, xt::all(), xt::all(), xt::all());
        xt::view(scores, xt::range(view_index_scores, view_index_scores + num_proposals_scores), xt::all()) = xt::reshape_view(output_scores, {num_proposals_scores, num_classes});
        view_index_scores += num_proposals_scores;

        // Keypoints extraction will be done later according to the boxes that surpass the threshold
        outputs_keypoints[i / 3] = tensors[i + 2];
    }
    return Triple{outputs_boxes, scores, outputs_keypoints};
}

std::vector<Decodings> yolov8pose_postprocess(std::vector<HailoTensorPtr> &tensors,
                                              std::vector<int> network_dims,
                                              std::vector<int> strides,
                                              int regression_length,
                                              int num_classes)
{
    std::vector<Decodings> decodings;
    if (tensors.size() == 0)
    {
        return decodings;
    }

    Triple boxes_scores_keypoints = get_boxes_scores_keypoints(tensors, num_classes, regression_length);
    std::vector<HailoTensorPtr> raw_boxes = boxes_scores_keypoints.boxes;
    xt::xarray<float> scores = boxes_scores_keypoints.scores;
    std::vector<HailoTensorPtr> raw_keypoints = boxes_scores_keypoints.keypoints;

    // Decode the boxes and keypoints
    decodings = decode_boxes_and_keypoints(raw_boxes, scores, raw_keypoints, network_dims, strides, regression_length);

    // Filter with NMS
    auto decodings_after_nms = nms(decodings, IOU_THRESHOLD, true);

    return decodings_after_nms;
}

/**
 * @brief yolov8 postprocess
 *        Provides network specific paramters
 *
 * @param roi  -  HailoROIPtr
 *        The roi that contains the ouput tensors
 */

std::pair<std::vector<KeyPt>, std::vector<PairPairs>> yolov8(HailoROIPtr roi)
{
    // anchor params
    int regression_length = 15;
    std::vector<int> strides = {8, 16, 32};
    std::vector<int> network_dims = {640, 640};

    std::vector<HailoTensorPtr> tensors = roi->get_tensors();
    auto filtered_decodings = yolov8pose_postprocess(tensors, network_dims, strides, regression_length, NUM_CLASSES);

    std::vector<HailoDetection> detections;

    for (auto &dec : filtered_decodings)
    {
        HailoDetection detection = dec.detection_box;
        std::pair<std::vector<KeyPt>, std::vector<PairPairs>> keypoints_and_pairs = process_single_decoding(dec, network_dims, 0.0f);
        std::vector<KeyPt> scaled_keypoints = keypoints_and_pairs.first;
        // Create an empty xarray with the correct shape
        // xt::xarray<float> landmarks = xt::empty<float>({18, 3});
        xt::xarray<float> landmarks = xt::empty<float>({int(scaled_keypoints.size()), 3});

        // Fill the xarray with the data from the vector
        for (size_t i = 0; i < scaled_keypoints.size(); ++i)
        {
            landmarks(i, 0) = scaled_keypoints[i].xs;
            landmarks(i, 1) = scaled_keypoints[i].ys;
            landmarks(i, 2) = scaled_keypoints[i].joints_scores;
        }

        hailo_common::add_landmarks_to_detection(detection, "centerpose", landmarks, SCORE_THRESHOLD, JOINT_PAIRS);
        detections.push_back(detection);
    }

    hailo_common::add_detections(roi, detections);

    std::pair<std::vector<KeyPt>, std::vector<PairPairs>> keypoints_and_pairs = filter_keypoints(filtered_decodings, network_dims);

    return keypoints_and_pairs;
}

//******************************************************************
//  DEFAULT FILTER
//******************************************************************

void filter(HailoROIPtr roi)
{
    yolov8(roi);
}
void filter_letterbox(HailoROIPtr roi)
{
    filter(roi);
    // Resize Letterbox
    HailoBBox roi_bbox = hailo_common::create_flattened_bbox(roi->get_bbox(), roi->get_scaling_bbox());
    auto detections = hailo_common::get_hailo_detections(roi);
    for (auto &detection : detections)
    {
        auto detection_bbox = detection->get_bbox();
        auto xmin = (detection_bbox.xmin() * roi_bbox.width()) + roi_bbox.xmin();
        auto ymin = (detection_bbox.ymin() * roi_bbox.height()) + roi_bbox.ymin();
        auto xmax = (detection_bbox.xmax() * roi_bbox.width()) + roi_bbox.xmin();
        auto ymax = (detection_bbox.ymax() * roi_bbox.height()) + roi_bbox.ymin();

        HailoBBox new_bbox(xmin, ymin, xmax - xmin, ymax - ymin);
        detection->set_bbox(new_bbox);
    }

    // Clear the scaling bbox of main roi because all detections are fixed.
    roi->clear_scaling_bbox();
}