/**
 * Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
 * Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)
 **/
#include <algorithm>
#include <cmath>
#include <iterator>
#include <string>
#include <tuple>
#include <vector>

#include "common/math.hpp"
#include "common/tensors.hpp"
#include "common/nms.hpp"
#include "json_config.hpp"
#include "scrfd.hpp"
#include "xtensor/xarray.hpp"
#include "xtensor/xio.hpp"
#include "xtensor/xpad.hpp"
#include "xtensor/xview.hpp"
#include "hailo_xtensor.hpp"
#include "rapidjson/document.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/error/en.h"
#include "rapidjson/filereadstream.h"
#include "rapidjson/schema.h"

// Teporary values
#define SCRFD_WIDTH (640)
#define SCRFD_HEIGHT (640)


std::vector<std::string> BOXES_10g {"scrfd_10g/conv42",
                                    "scrfd_10g/conv50",
                                    "scrfd_10g/conv57"};
std::vector<std::string> CLASSES_10g {"scrfd_10g/conv41",
                                      "scrfd_10g/conv49",
                                      "scrfd_10g/conv56"};
std::vector<std::string> LANDMARKS_10g {"scrfd_10g/conv43",
                                        "scrfd_10g/conv51",
                                        "scrfd_10g/conv58"};

std::vector<std::string> BOXES_2_5g {"scrfd_2_5g/conv43",
                                     "scrfd_2_5g/conv50",
                                     "scrfd_2_5g/conv56"};
std::vector<std::string> CLASSES_2_5g {"scrfd_2_5g/conv42",
                                       "scrfd_2_5g/conv49",
                                       "scrfd_2_5g/conv55"};
std::vector<std::string> LANDMARKS_2_5g {"scrfd_2_5g/conv44",
                                         "scrfd_2_5g/conv51",
                                         "scrfd_2_5g/conv57"};

std::vector<std::string> BOXES;
std::vector<std::string> CLASSES;
std::vector<std::string> LANDMARKS;

#if __GNUC__ > 8
#include <filesystem>
namespace fs = std::filesystem;
#else
#include <experimental/filesystem>
namespace fs = std::experimental::filesystem;
#endif

ScrfdParams *init(const std::string config_path, const std::string function_name)
{
    int image_width;
    int image_height;
    xt::xarray<float> anchor_variance;
    xt::xarray<int> anchor_steps;
    std::vector<std::vector<int>> anchor_min_size;
    float score_threshold;
    float iou_threshold;
    int num_branches;
    if (!fs::exists(config_path))
    {
        std::cerr << "Config file doesn't exist, using default parameters" << std::endl;
        if (function_name.std::string::compare("scrfd") == 0)
        {
            image_width = SCRFD_WIDTH;
            image_height = SCRFD_HEIGHT;
            anchor_variance = {0.1, 0.2};
            anchor_steps = {8, 16, 32};
            anchor_min_size = {{16, 32}, {64, 128}, {256, 512}};
            num_branches = anchor_min_size.size();
            score_threshold = 0.4;
            iou_threshold = 0.4;
        }
        else
        {
            throw std::runtime_error("Function name is not valid, should be lightface or retinaface");
        }
    }
    else // there is a config path
    {
        char config_buffer[4096];
        const char *json_schema = R""""({
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "required": [
            "image_width",
            "image_height",
            "anchor_variance",
            "anchor_steps",
            "anchor_min_size",
            "score_threshold",
            "iou_threshold"
        ],
        "properties": {
            "image_width": {
                "type": "integer"
            },
            "image_height": {
                "type": "integer"
            },
            "anchor_variance": {
                "type": "array",
                "items": {
                    "type": "number"
                }
            },
            "anchor_steps": {
                "type": "array",
                "items": {
                    "type": "integer"
                }
            },
            "anchor_min_size": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                }
            },
            "score_threshold": {
                "type": "number"
            },
            "iou_threshold": {
                "type": "number"
            }
        }
    })"""";
        std::FILE *fp = fopen(config_path.c_str(), "r");
        if (fp == nullptr)
        {
            throw std::runtime_error("JSON config file is not valid");
        }
        rapidjson::FileReadStream stream(fp, config_buffer, sizeof(config_buffer));
        bool valid = common::validate_json_with_schema(stream, json_schema);
        if (valid)
        {
            rapidjson::Document doc_config_json;
            doc_config_json.ParseStream(stream);

            auto config_anchor_variance = doc_config_json["anchor_variance"].GetArray();
            auto config_anchor_steps = doc_config_json["anchor_steps"].GetArray();
            auto config_anchor_min_size = doc_config_json["anchor_min_size"].GetArray();

            // parse anchors
            std::vector<float> anchor_variance_vector;
            std::vector<int> anchor_steps_vector;

            for (uint i = 0; i < config_anchor_variance.Size(); i++)
            {
                anchor_variance_vector.emplace_back(config_anchor_variance[i].GetFloat());
            }

            for (uint i = 0; i < config_anchor_steps.Size(); i++)
            {
                anchor_steps_vector.emplace_back(config_anchor_steps[i].GetInt());
            }
            for (uint i = 0; i < config_anchor_min_size.Size(); i++)
            {
                uint anchor_size = config_anchor_min_size[i].Size();
                std::vector<int> anchor;
                for (uint j = 0; j < anchor_size; j++)
                {
                    anchor.emplace_back(config_anchor_min_size[i].GetArray()[j].GetInt());
                }
                anchor_min_size.emplace_back(anchor);
            }
            anchor_variance = xt::adapt(anchor_variance_vector);
            anchor_steps = xt::adapt(anchor_steps_vector);
            image_width = doc_config_json["image_width"].GetInt();
            image_height = doc_config_json["image_height"].GetInt();
            score_threshold = doc_config_json["score_threshold"].GetFloat();
            iou_threshold = doc_config_json["iou_threshold"].GetFloat();
            num_branches = anchor_min_size.size();
        }
        else
        {
            throw std::runtime_error("JSON config file is not valid");
        }
    }

    // Calculate the anchors based on the image size, step size, and feature map.
    xt::xarray<float> anchors;
    anchors = get_anchors_scrfd(anchor_min_size, anchor_steps, image_width, image_height);
    // Using the anchors, create a multiplier that will be used against the tensor results.
    ScrfdParams *params = new ScrfdParams(anchors, anchor_variance, anchor_min_size, score_threshold, iou_threshold, num_branches);
    return params;
}

void free_resources(void *params_void_ptr)
{
    ScrfdParams *params = reinterpret_cast<ScrfdParams *>(params_void_ptr);
    delete params;
}

//******************************************************************
// SETUP - ANCHOR EXTRACTION
//******************************************************************
xt::xarray<float> get_anchors_scrfd(const std::vector<std::vector<int>> &anchor_min_sizes,
                                    const xt::xarray<int> &anchor_steps,
                                    const int image_width,
                                    const int image_height)
{
    int total_anchors, num_anchors, width, height;
    total_anchors = num_anchors = width = height = 0;

    // Initialize the anchors to the given size. This way we can fill them in-place
    // instead of concatenating, saving lots of time. 
    for (uint index = 0; index < anchor_min_sizes.size(); index++)
    {
        width = image_width / anchor_steps[index];
        height = image_height / anchor_steps[index];
        num_anchors = anchor_min_sizes[index].size();
        total_anchors += width * height * num_anchors;
    }
    xt::xarray<float> anchors = xt::zeros<float>({total_anchors, 4});

    int anchor_range = 0;
    for (uint index = 0; index < anchor_min_sizes.size(); index++)
    {
        // First build a meshgrid of centers (x,y) for the anchors
        int width = image_width / anchor_steps[index];
        int height = image_height / anchor_steps[index];
        num_anchors = anchor_min_sizes[index].size();
        xt::xarray<float> anchor_centers_stack = xt::transpose(xt::stack(xt::meshgrid(xt::arange(0, width), xt::arange(0, height)))) * anchor_steps[index];
        auto anchor_centers_paired = xt::reshape_view(anchor_centers_stack, {width * height, 2});

        // Normalize the centers to the size of the anchor branch
        xt::col(anchor_centers_paired, 0) = xt::col(anchor_centers_paired, 0) / image_height;
        xt::col(anchor_centers_paired, 1) = xt::col(anchor_centers_paired, 1) / image_width;
        auto anchor_centers = xt::repeat(anchor_centers_paired, num_anchors, 0);

        // Create sclaes to match the anchor centers
        xt::xarray<float> anchor_scales = xt::ones_like(anchor_centers) * anchor_steps[index];
        xt::col(anchor_scales, 0) = xt::col(anchor_scales, 0) / image_height;
        xt::col(anchor_scales, 1) = xt::col(anchor_scales, 1) / image_width;

        // Concat and fill the anchors in place
        auto anchor_layer = xt::concatenate(xt::xtuple(anchor_centers, anchor_scales), 1);
        xt::view(anchors, xt::range(anchor_range, anchor_range + anchor_centers.shape(0)), xt::all()) = anchor_layer;
        anchor_range += width * height * num_anchors;
    }
    return anchors;
}

//******************************************************************
// BOX/LANDMARK DECODING
//******************************************************************
xt::xarray<float> decode_landmarks_scrfd(const xt::xarray<float> &landmark_detections,
                                        const xt::xarray<float> &anchors)
{
    // Decode the boxes relative to their anchors.
    // There are 5 landmarks paired in sets of 2 (x and y values),
    // so we need to tile our anchors by 5
    xt::xarray<float> landmarks = xt::tile(xt::view(anchors, xt::all(), xt::range(0, 2)), {1, 5}) + landmark_detections * xt::tile(xt::view(anchors, xt::all(), xt::range(2, 4)), {1, 5});
    return landmarks;
}

xt::xarray<float> decode_boxes_scrfd(const xt::xarray<float> &box_detections,
                                     const xt::xarray<float> &anchors)
{
    // Initalize the boxes matrix at the expected size
    xt::xarray<float> boxes = xt::zeros<float>(box_detections.shape());
    // Decode the boxes relative to their anchors in place
    xt::col(boxes, 0) = xt::col(anchors, 0) - (xt::col(box_detections, 0) * xt::col(anchors, 2));
    xt::col(boxes, 1) = xt::col(anchors, 1) - (xt::col(box_detections, 1) * xt::col(anchors, 3));
    xt::col(boxes, 2) = xt::col(anchors, 0) + (xt::col(box_detections, 2) * xt::col(anchors, 2));
    xt::col(boxes, 3) = xt::col(anchors, 1) + (xt::col(box_detections, 3) * xt::col(anchors, 3));
    return boxes;
}

std::tuple<xt::xarray<float>, xt::xarray<float>, xt::xarray<float>> detect_decode_branch(std::map<std::string, HailoTensorPtr> &tensors,
                                                                                        const xt::xarray<uint8_t> &boxes_quant,
                                                                                        const xt::xarray<uint8_t> &classes_quant,
                                                                                        const xt::xarray<uint8_t> &landmarks_quant,
                                                                                        const xt::xarray<float> &anchors,
                                                                                        const float score_threshold,
                                                                                        const int i,
                                                                                        const int steps)
{
    // Filter scores that pass threshold, quantize the score threshold
    auto scores_quant = xt::col(classes_quant, 1);
    xt::xarray<int> threshold_indices = xt::flatten_indices(xt::argwhere(scores_quant > tensors[CLASSES[i]]->quantize(score_threshold)));
    
    if (threshold_indices.shape(0) == 0)
        return xt::xtuple(xt::empty<float>({0}), xt::empty<float>({0}), xt::empty<float>({0}));

    // Filter and dequantize boxes
    xt::xarray<uint8_t> high_boxes_quant = xt::view(boxes_quant, xt::keep(threshold_indices), xt::all());
    auto high_boxes_dequant = common::dequantize(high_boxes_quant,
                                                tensors[BOXES[i]]->vstream_info().quant_info.qp_scale,
                                                tensors[BOXES[i]]->vstream_info().quant_info.qp_zp);
    // Filter and dequantize scores
    xt::xarray<uint8_t> high_scores_quant = xt::view(scores_quant, xt::keep(threshold_indices));
    auto high_scores_dequant = common::dequantize(high_scores_quant,
                                                tensors[CLASSES[i]]->vstream_info().quant_info.qp_scale,
                                                tensors[CLASSES[i]]->vstream_info().quant_info.qp_zp);
    // Filter and dequantize landmarks
    xt::xarray<uint8_t> high_landmarks_quant = xt::view(landmarks_quant, xt::keep(threshold_indices), xt::all());
    auto high_landmarks_dequant = common::dequantize(high_landmarks_quant,
                                                    tensors[LANDMARKS[i]]->vstream_info().quant_info.qp_scale,
                                                    tensors[LANDMARKS[i]]->vstream_info().quant_info.qp_zp);
    // Filter anchors and use them to decode boxes/landmarks
    auto stepped_inds = threshold_indices + steps;
    auto high_anchors = xt::view(anchors, xt::keep(stepped_inds), xt::all());
    xt::xarray<float> decoded_boxes = decode_boxes_scrfd(high_boxes_dequant, high_anchors);
    xt::xarray<float> decoded_landmarks = decode_landmarks_scrfd(high_landmarks_dequant, high_anchors);

    // Return boxes, scores, and landmarks
    return xt::xtuple(decoded_boxes, high_scores_dequant, decoded_landmarks);
}

std::tuple<std::vector<xt::xarray<float>>,
            std::vector<xt::xarray<float>>,
            std::vector<xt::xarray<float>>>
detect_boxes_and_landmarks(std::map<std::string, HailoTensorPtr> &tensors,
                           const std::vector<xt::xarray<uint8_t>> &boxes_quant,
                           const std::vector<xt::xarray<uint8_t>> &classes_quant,
                           const std::vector<xt::xarray<uint8_t>> &landmarks_quant,
                           const xt::xarray<float> &anchors,
                           const float score_threshold)
{
    std::vector<xt::xarray<float>> high_scores_dequant(CLASSES.size());
    std::vector<xt::xarray<float>> decoded_boxes(BOXES.size());
    std::vector<xt::xarray<float>> decoded_landmarks(LANDMARKS.size());

    int steps = 0;
    for (uint i = 0; i < CLASSES.size(); ++i)
    {
        auto boxes_scores_landmarks = detect_decode_branch(tensors,
                                                           boxes_quant[i],
                                                           classes_quant[i],
                                                           landmarks_quant[i],
                                                           anchors, score_threshold, i, steps);
        decoded_boxes[i] = std::get<0>(boxes_scores_landmarks);
        high_scores_dequant[i] = std::get<1>(boxes_scores_landmarks);
        decoded_landmarks[i] = std::get<2>(boxes_scores_landmarks);
        steps += classes_quant[i].shape(0);
    }

    return std::tuple<std::vector<xt::xarray<float>>,
                      std::vector<xt::xarray<float>>,
                      std::vector<xt::xarray<float>>>(std::move(decoded_boxes),
                                                      std::move(high_scores_dequant),
                                                      std::move(decoded_landmarks));
}

//******************************************************************
// DETECTION/LANDMARKS EXTRACTION & ENCODING
//******************************************************************
void encode_detections(std::vector<HailoDetection> &objects,
                       std::vector<xt::xarray<float>> &detection_boxes,
                       std::vector<xt::xarray<float>> &scores,
                       std::vector<xt::xarray<float>> &landmarks)
{
    // Here we will package the processed detections into the HailoDetection meta
    // The detection meta will hold the following items:
    float confidence, w, h, xmin, ymin = 0.0f;
    // There is only 1 class in this network (face) so there is no need for label.
    std::string label = "face";
    // Iterate over our results
    for (uint i = 0; i < CLASSES.size(); ++i)
    {
        for (uint index = 0; index < scores[i].size(); ++index)
        {
            confidence = scores[i](index);                                  // Get the score for this detection
            xmin = detection_boxes[i](index, 0);                            // Box xmin, relative to image size
            ymin = detection_boxes[i](index, 1);                            // Box ymin, relative to image size
            w = (detection_boxes[i](index, 2) - detection_boxes[i](index, 0)); // Box width, relative to image size
            h = (detection_boxes[i](index, 3) - detection_boxes[i](index, 1)); // Box height, relative to image size

            // Once all parameters are calculated, push them into the meta
            // Class = 1 since centerpose only detects people
            HailoBBox bbox(xmin, ymin, w, h);
            HailoDetection detected_face(bbox, label, confidence);

            xt::xarray<float> keypoints_raw = xt::row(landmarks[i], index);
            // The keypoints are flatten, reshape them to 2 * num_keypoints.
            int num_keypoints = keypoints_raw.shape(0) / 2;
            auto face_keypoints = xt::reshape_view(keypoints_raw, {num_keypoints, 2});
            hailo_common::add_landmarks_to_detection(detected_face, "scrfd", face_keypoints);

            objects.push_back(detected_face); // Push the detection to the objects vector
        }
    }
}

std::vector<HailoDetection> face_detection_postprocess(std::map<std::string, HailoTensorPtr> &tensors_by_name,
                                                       const xt::xarray<float> &anchors,
                                                       const float score_threshold,
                                                       const float iou_threshold,
                                                       const int num_branches,
                                                       const int total_classes)
{
    std::vector<HailoDetection> objects; // The detection meta we will eventually return

    //-------------------------------
    // TENSOR GATHERING
    //-------------------------------
    // The output layers fall into hree categories: boxes, classes(scores), and lanmarks(x,y for each)
    std::vector<xt::xarray<uint8_t>> box_layers_quant;
    std::vector<xt::xarray<uint8_t>> class_layers_quant;
    std::vector<xt::xarray<uint8_t>> landmarks_layers_quant;

    for (uint i = 0; i < BOXES.size(); ++i)
    {
        // Extract the boxes
        xt::xarray<uint8_t> xdata_boxes = common::get_xtensor(tensors_by_name[BOXES[i]]);
        auto num_boxes = (int)xdata_boxes.shape(0) * (int)xdata_boxes.shape(1) * ((int)xdata_boxes.shape(2) / 4);
        auto xdata_boxes_reshaped = xt::reshape_view(xdata_boxes, {num_boxes, 4}); // Resize to be by the 4 parameters for a box
        box_layers_quant.emplace_back(std::move(xdata_boxes_reshaped));

        // Extract the classes
        xt::xarray<uint8_t> xdata_classes = common::get_xtensor(tensors_by_name[CLASSES[i]]);
        auto num_classes = (int)xdata_classes.shape(0) * (int)xdata_classes.shape(1) * ((int)xdata_classes.shape(2) / total_classes);
        auto xdata_classes_reshaped = xt::reshape_view(xdata_classes, {num_classes, total_classes}); // Resize to be by the total_classes available classes
        class_layers_quant.emplace_back(std::move(xdata_classes_reshaped));

        // Extract the landmarks
        xt::xarray<uint8_t> xdata_landmarks = common::get_xtensor(tensors_by_name[LANDMARKS[i]]);
        auto num_landmarks = (int)xdata_landmarks.shape(0) * (int)xdata_landmarks.shape(1) * ((int)xdata_landmarks.shape(2) / 10);
        auto xdata_landmarks_reshaped = xt::reshape_view(xdata_landmarks, {num_landmarks, 10}); // Resize to be by the (x,y) for each of the 5 landmarks (2*5=10)
        landmarks_layers_quant.emplace_back(std::move(xdata_landmarks_reshaped));
    }

    //-------------------------------
    // CALCULATION AND EXTRACTION
    //-------------------------------

    // Extract boxes and landmarks
    auto boxes_and_landmarks = detect_boxes_and_landmarks(tensors_by_name,
                                                          box_layers_quant,
                                                          class_layers_quant,
                                                          landmarks_layers_quant,
                                                          anchors,
                                                          score_threshold);

    // //-------------------------------
    // // RESULTS ENCODING
    // //-------------------------------

    // // Encode the individual boxes/keypoints and package them into the meta
    encode_detections(objects,
                      std::get<0>(boxes_and_landmarks),
                      std::get<1>(boxes_and_landmarks),
                      std::get<2>(boxes_and_landmarks));

    // // Perform nms to throw out similar detections
    common::nms(objects, iou_threshold);

    return objects;
}

//******************************************************************
//  SCRFD POSTPROCESS
//******************************************************************
void scrfd(HailoROIPtr roi, void *params_void_ptr)
{
    /*
     *  The lightface network outputs tensors in 4 sets of 2 (totaling 8 layers).
     *  Each set has a layer describing bounding boxes of detections, and a layer
     *  of class scores for each corresponding box. Each set of boxes and scores
     *  operate at a different scale of the feature set. The 4 different scales
     *  give us decent coverage of the possible sizes objects can take in the image.
     *  Since the detections output by the network are anchor boxes, we need to
     *  multiply them by anchors that we determine in advanced using the parameters below.
     */
    /*
     *  The retinaface operates under the same principles as the lightface network
     *  below, however here we include a set of landmarks for each detection box.
     *  This means that instead of sets of 2 tensors, the newtork outputs 3 sets
     *  of 3 tensors (totalling in 9 output layers). So each set has a tensor for
     *  boxes, corresponding scores, and corresponding landmarks. Like in lightface,
     *  we need to trabsform the boxes using anchors determined by the parameters below.
     */
    /*
     *  SCRFD is also a face detection + landmarks network like retinaface below.
     *  It uses the same tensor scheme but different decoding stratedgy.
     *  Overall differences lie in performance and resolution.
     */
    // Get the output layers from the hailo frame.
    ScrfdParams *params = reinterpret_cast<ScrfdParams *>(params_void_ptr);
    if (!roi->has_tensors())
        return;
    std::map<std::string, HailoTensorPtr> tensors_by_name = roi->get_tensors_by_name();

    // Extract the detection objects using the given parameters.
    std::vector<HailoDetection> detections = face_detection_postprocess(tensors_by_name, params->anchors,
                                                                        params->score_threshold, params->iou_threshold,
                                                                        params->num_branches, 1);

    // Update the frame with the found detections.
    hailo_common::add_detections(roi, detections);
}


void scrfd_2_5g(HailoROIPtr roi, void *params_void_ptr)
{
    ScrfdParams *params = reinterpret_cast<ScrfdParams *>(params_void_ptr);
    BOXES = BOXES_2_5g;
    CLASSES = CLASSES_2_5g;
    LANDMARKS = LANDMARKS_2_5g;
    scrfd(roi, params);
}


void scrfd_10g(HailoROIPtr roi, void *params_void_ptr)
{
    ScrfdParams *params = reinterpret_cast<ScrfdParams *>(params_void_ptr);
    BOXES = BOXES_10g;
    CLASSES = CLASSES_10g;
    LANDMARKS = LANDMARKS_10g;
    scrfd(roi, params);
}

//******************************************************************
//  DEFAULT FILTER
//******************************************************************
void filter(HailoROIPtr roi, void *params_void_ptr)
{
    // Default scrfd_10g
    ScrfdParams *params = reinterpret_cast<ScrfdParams *>(params_void_ptr);
    BOXES = BOXES_10g;
    CLASSES = CLASSES_10g;
    LANDMARKS = LANDMARKS_10g;
    scrfd(roi, params);
}

void scrfd_10g_letterbox(HailoROIPtr roi, void *params_void_ptr)
{
    scrfd_10g(roi, params_void_ptr);
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

void scrfd_2_5g_letterbox(HailoROIPtr roi, void *params_void_ptr)
{
    scrfd_2_5g(roi, params_void_ptr);
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