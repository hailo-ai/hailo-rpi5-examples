#include "yolov5seg.hpp"
#include "xtensor/xsort.hpp"
#include "xtensor/xpad.hpp"
#include "hailo_common.hpp"
#include "common/tensors.hpp"
#include "common/nms.hpp"
#include "common/labels/coco_eighty.hpp"
#include "mask_decoding.hpp"

#include "json_config.hpp"
#include "rapidjson/document.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/error/en.h"
#include "rapidjson/filereadstream.h"
#include "rapidjson/schema.h"

#include <thread>
#include <future>
#include <iterator>
#if __GNUC__ > 8
#include <filesystem>
namespace fs = std::filesystem;
#else
#include <experimental/filesystem>
namespace fs = std::experimental::filesystem;
#endif

// the net returns 32 values representing the mask coefficients, and 4 values representing the box coordinates
#define MASK_CO 32
#define BOX_CO 4

/**
 * @brief  Compute sigmoid's inverse
 */
inline float inverse_sigmoid(float y) { return std::log(y/(1-y));}

/**
 * @brief  perform quantization
 */
inline uint16_t quant(float num, float qp_zp, float qp_scale) { return uint16_t((num / qp_scale)  + qp_zp); }

/**
 * @brief  perform dequantization
 */
inline float dequant(uint16_t num, float qp_zp, float qp_scale) { return (float(num) - qp_zp) * qp_scale;}

/*
 * @brief Creates the grid and the anchor grid that will be used for each decoding
 *
 * @param anchors xarray, initialized in creation of Yolov5segParams
 * @param stride
 * @param nx shape[0] of the branch
 * @param ny shape[1] of the branch
 * @param num_anchors is the number of anchors per branch / 2
 */
std::tuple<xt::xarray<float>, xt::xarray<float>> make_grid(xt::xarray<float> &anchors, const int stride, const int nx, const int ny, const int num_anchors)
{
    xt::xarray<int> x = xt::arange(nx);
    xt::xarray<int> y = xt::arange(ny);
    auto mesh = xt::meshgrid(y, x);
    auto yv = std::get<0>(mesh);
    auto xv = std::get<1>(mesh);
    // making grid
    auto stack = xt::stack(xt::xtuple(xv, yv), 2);
    stack.reshape({1, ny, nx, 2});
    xt::xarray<float> grid = xt::broadcast(stack, {num_anchors, ny, nx, 2}) - 0.5;
    xt::xarray<float> transposed_grid = xt::transpose(grid, {1, 2, 0, 3}); // num_anchors, h, w, features
    // making anchor grid
    anchors *= stride;
    anchors.reshape({num_anchors, 1, 1, 2});
    xt::xarray<float> anchor_grid = xt::broadcast(anchors, {num_anchors, ny, nx, 2});
    xt::xarray<float> transposed_anchor_grid = xt::transpose(anchor_grid, {1, 2, 0, 3}); // num_anchors, h, w, features
    return std::tuple<xt::xarray<float>, xt::xarray<float>>(std::move(transposed_grid), std::move(transposed_anchor_grid));
}

/*
 * @brief Returns a vector of indices, of detections that have: is_object * max(class_confidence) > score_threshold
 *
 * @param all_scores an xview with the confidence scores for each class, for each detection
 * @param all_is_object an xview with the confidence that this detection is an object, for each detection
 * @param score_threshold float
 */
auto filter_above_threshold(auto &all_scores, auto &is_object_threshold, const float score_threshold, const uint16_t threshold_quantized, const float qp_zp, const float qp_scale)
{
    std::vector<uint> indices;
    std::vector<float> scores;
    std::vector<uint> classes;
    int this_index;
    float conf_deq, is_object_deq;
    uint16_t is_object;
    for (uint i = 0; i < is_object_threshold.size(); i++)
    {
        // first check if the object parameter is bigger than threshold
        is_object = is_object_threshold(i, 0);
        if (is_object > threshold_quantized)
        {
            this_index = xt::argmax(xt::row(all_scores, i))(0) + 1;
            // dequantize and decode
            conf_deq = sigmoid(dequant(all_scores(i, this_index - 1), qp_zp, qp_scale));
            is_object_deq = sigmoid(dequant(is_object, qp_zp, qp_scale));
            if (conf_deq*is_object_deq > score_threshold)
            {
                indices.emplace_back(i);
                scores.emplace_back(conf_deq * is_object_deq);
                classes.emplace_back(this_index);
        }
    }
    }
    return std::tuple<std::vector<uint>, std::vector<float>, std::vector<uint>>(std::move(indices), std::move(scores), std::move(classes));
}

/*
 * @brief Gets the xviews of the decoded and filtered results, and adds them to a vector of HailoDetections
 *
 * @param size int representing amount of detections
 * @param boxes xview of (x, y, w, h), x and y are the center of the box
 * @param is_object an xview with the confidence that this detection is an object, for each detection
 * @param scores an xview with the confidence scores for each class, for each detection
 * @param masks an xview with 32 coefficients representing a mask per detection
 * @param objects a vecor of HailoDetections, to which the detections will be added
 *  */
std::vector<HailoDetection> create_hailo_detections(auto &scores_vec, auto &classes_vec, auto &xy, auto wh, auto &masks, const int input_width, const int input_height)
{
    int class_index;
    float confidence, w, h, x, y = 0.0;
    std::vector<HailoDetection> objects;
    for (uint i = 0; i < scores_vec.size(); i++)
    {
        // Get the box parameters for this box
        x = (xy(i, 0)) / input_width;
        y = (xy(i, 1)) / input_height;
        w = (wh(i, 0)) / input_width;
        h = (wh(i, 1)) / input_height;
        // x and y represented center of box, so they need to be changed to left bottom corner
        HailoBBox bbox(x - w / 2, y - h / 2, w, h);
        class_index = classes_vec[i];
        std::string label = common::coco_eighty[class_index];
        confidence = scores_vec[i];
        // create mask
        xt::xarray<float> mask_coefficients = xt::squeeze(xt::view(masks, xt::keep(i), xt::all()));
        HailoDetection detected_instance(bbox, class_index, label, confidence);
        std::vector<float> data(mask_coefficients.shape(0));
        memcpy(data.data(), mask_coefficients.data(), sizeof(float) * mask_coefficients.shape(0));
        // create the detection itself
        detected_instance.add_object((std::make_shared<HailoMatrix>(data, mask_coefficients.shape(0), 1)));
        objects.push_back(detected_instance);
    }
    return objects;
}

/*
 * @brief Does the decoding and the filtering for the output, and adds the results to the HailoDetections vector
 *
 *  */
std::vector<HailoDetection> yolov5_decoding(xt::xarray<uint16_t> &output, const int stride, xt::xarray<float> &anchors, xt::xarray<float> &grid, xt::xarray<float> &anchor_grid, const int num_anchors, const float score_threshold, float qp_zp, float qp_scale, const int input_width, const int input_height)
{
    int h = output.shape()[0];
    int w = output.shape()[1];
    int num_classes = (output.shape()[2] / 3) - BOX_CO - 1 - MASK_CO;

    // prepare data for filter function
    auto all_decoded = xt::reshape_view(output, {num_anchors * h * w, BOX_CO + 1 + num_classes + MASK_CO}); // {number of detections, 117}
    auto all_is_object = xt::view(all_decoded, xt::all(), xt::range(4, 5));
    auto all_scores = xt::view(all_decoded, xt::all(), xt::range(5, num_classes + 5));
    // quantize the score threshold + "undecode" it (do inverse of sigmoid), to avoid doing dequantization and decoding on all class scores
    uint16_t threshold_quantized = quant(inverse_sigmoid(score_threshold), qp_zp, qp_scale);
    auto filtered = filter_above_threshold(all_scores, all_is_object, score_threshold, threshold_quantized, qp_zp, qp_scale);
    std::vector<uint> indices = std::get<0>(filtered);
    std::vector<float> scores_vec = std::get<1>(filtered);
    std::vector<uint> classes_vec = std::get<2>(filtered);

    // filter xy and grid
    auto xy = xt::view(all_decoded, xt::all(), xt::range(_, 2));
    auto reshaped_grid = xt::reshape_view(grid, xy.shape());
    auto filtered_xy = xt::view(xy, xt::keep(indices), xt::all());
    auto filtered_grid = xt::view(reshaped_grid, xt::keep(indices), xt::all());
    // dequantize and decode xy
    xt::xarray<float> deq_xy = (filtered_xy - qp_zp) * qp_scale;
    deq_xy = (xtensor_sigmoid(deq_xy) * 2 + filtered_grid) * stride;

    // filter wh and anchor grid
    auto wh = xt::view(all_decoded, xt::all(), xt::range(2, 4));
    auto reshaped_anchor_grid = xt::reshape_view(anchor_grid, wh.shape());
    auto filtered_wh = xt::view(wh, xt::keep(indices), xt::all());
    auto filtered_anchor_grid = xt::view(reshaped_anchor_grid, xt::keep(indices), xt::all());
    // dequantize and decode wh
    xt::xarray<float> deq_wh = (filtered_wh - qp_zp) * qp_scale;
    deq_wh = xt::square(xtensor_sigmoid(deq_wh) * 2) * filtered_anchor_grid;

    // filter and dequantize masks
    auto filtered_masks = xt::view(all_decoded, xt::keep(indices), xt::range(num_classes + 5, _));
    xt::xarray<float> masks = (filtered_masks - qp_zp) * qp_scale;

    // create HailoDetections for the NMS and the mask decoding
    std::vector<HailoDetection> objects = create_hailo_detections(scores_vec, classes_vec, deq_xy, deq_wh, masks, input_width, input_height);
    return objects;
}

/*
 * @brief Does dequantize and decoding for each output seperately
 *
 *  */
std::vector<HailoDetection> post_per_branch(std::string branch_name, const int index, std::map<std::string, HailoTensorPtr> tensors, std::vector<xt::xarray<float>> anchor_list, std::vector<int> stride_list, const float iou_threshold, const float score_threshold, std::vector<xt::xarray<float>> grids, std::vector<xt::xarray<float>> anchor_grids, const int num_anchors, const int input_width, const int input_height)
{
    auto output = common::get_xtensor_uint16(tensors[branch_name]);
    float qp_zp = tensors[branch_name]->vstream_info().quant_info.qp_zp;
    float qp_scale = tensors[branch_name]->vstream_info().quant_info.qp_scale;
    return yolov5_decoding(output, stride_list[index], anchor_list[index], grids[index], anchor_grids[index], num_anchors, score_threshold, qp_zp, qp_scale, input_width, input_height);
}

/*
 * @brief Does dequantize and decoding for each output, and then calls nms and decode masks
 *
 *  */
std::vector<HailoDetection> yolov5seg_post(auto &tensors, auto &anchor_list, auto &stride_list, const float iou_threshold, const float score_threshold, auto &grids, auto &anchor_grids, const int num_anchors, const int input_width, const int input_height, auto &outputs_name)
{
    auto proto_tensor = common::dequantize(common::get_xtensor(tensors[outputs_name[0]]), tensors[outputs_name[0]]->vstream_info().quant_info.qp_scale, tensors[outputs_name[0]]->vstream_info().quant_info.qp_zp);

    // run the postprocess for each branch seperately
    std::future<std::vector<HailoDetection>> t2 = std::async(post_per_branch, outputs_name[1], 2, tensors, anchor_list, stride_list, iou_threshold, score_threshold, grids, anchor_grids, num_anchors, input_width, input_height);
    std::future<std::vector<HailoDetection>> t1 = std::async(post_per_branch, outputs_name[2], 1, tensors, anchor_list, stride_list, iou_threshold, score_threshold, grids, anchor_grids, num_anchors, input_width, input_height);
    std::future<std::vector<HailoDetection>> t0 = std::async(post_per_branch, outputs_name[3], 0, tensors, anchor_list, stride_list, iou_threshold, score_threshold, grids, anchor_grids, num_anchors, input_width, input_height);
    std::vector<HailoDetection> d2 = t2.get();
    std::vector<HailoDetection> d1 = t1.get();
    std::vector<HailoDetection> d0 = t0.get();

    // concatenate all detections
    std::vector<HailoDetection> all_detections;
    all_detections.reserve(d0.size() + d1.size() + d2.size());
    all_detections.insert(all_detections.end(), d0.begin(), d0.end());
    all_detections.insert(all_detections.end(), d1.begin(), d1.end());
    all_detections.insert(all_detections.end(), d2.begin(), d2.end());

    common::nms(all_detections, iou_threshold);
    decode_masks(all_detections, proto_tensor);
    return all_detections;
}

Yolov5segParams *init(const std::string config_path, const std::string function_name)
{
    Yolov5segParams *params = new Yolov5segParams();
    if (!fs::exists(config_path))
    {
        std::cerr << "Config file doesn't exist, using default parameters" << std::endl;
    }
    else {
        char config_buffer[4096];
        const char *json_schema = R""""({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Generated schema for Root",
        "type": "object",
        "properties": {
            "iou_threshold": {
            "type": "number"
            },
            "score_threshold": {
            "type": "number"
            },
            "outputs_size": {
            "type": "array",
            "items": {
                "type": "number"
            }
            },
            "outputs_name": {
            "type": "array",
            "items": {
            "type": "string"
            }
            },
            "anchors": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {
                "type": "number"
                }
            }
            },
            "input_shape": {
            "type": "array",
            "items": {
                "type": "number"
            }
            },
            "strides": {
            "type": "array",
            "items": {
                "type": "number"
            }
            }
        },
        "required": [
            "iou_threshold",
            "score_threshold",
            "outputs_size",
            "anchors",
            "input_shape",
            "strides"
        ]
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

            params->iou_threshold = doc_config_json["iou_threshold"].GetFloat();
            params->score_threshold = doc_config_json["score_threshold"].GetFloat();

            // parse anchors
            auto config_anchors = doc_config_json["anchors"].GetArray();
            std::vector<xt::xarray<float>> anchors_vec;
            for (uint j = 0; j < config_anchors.Size(); j++)
            {
                uint size = config_anchors[j].GetArray().Size();
                std::vector<float> anchor;
                for (uint k = 0; k < size; k++)
                {
                    anchor.push_back(config_anchors[j].GetArray()[k].GetFloat());
                }
                auto anchors_tensor = xt::adapt(anchor);
                anchors_vec.push_back(anchors_tensor);
            }
            params->anchors = anchors_vec;
            
            // parse outputs_size
            auto config_outputs_size = doc_config_json["outputs_size"].GetArray();
            std::vector<int> outputs_size_vec;
            for (uint j = 0; j < config_outputs_size.Size(); j++)
            {
                outputs_size_vec.push_back(config_outputs_size[j].GetInt());
            }
            params->outputs_size = outputs_size_vec;

            // parse outputs_name
            auto config_outputs_name = doc_config_json["outputs_name"].GetArray();
            std::vector<std::string> outputs_name_vec;
            for (uint j = 0; j < config_outputs_name.Size(); j++)
            {
                outputs_name_vec.push_back(config_outputs_name[j].GetString());
            }
            params->outputs_name = outputs_name_vec;

            // parse input_shape
            auto config_input_shape = doc_config_json["input_shape"].GetArray();
            std::vector<int> input_shape_vec;
            for (uint j = 0; j < config_input_shape.Size(); j++)
            {
                input_shape_vec.push_back(config_input_shape[j].GetInt());
            }
            params->input_shape = input_shape_vec;

            // parse strides
            auto config_strides = doc_config_json["strides"].GetArray();
            std::vector<int> strides_vec;
            for (uint j = 0; j < config_strides.Size(); j++)
            {
                strides_vec.push_back(config_strides[j].GetInt());
            }
            params->strides = strides_vec;

        fclose(fp);
    } }
    std::vector<int> outputs_size = params->outputs_size;
    std::vector<xt::xarray<float>> anchors = params->anchors;
    std::vector<int> strides = params->strides;
    std::vector<xt::xarray<float>> grids;
    std::vector<xt::xarray<float>> anchor_grids;
    int num_anchors = 0;
    // create grid and anchor grid
    for (uint index = 0; index < outputs_size.size(); index++)
    {
        anchors[index] /= strides[index];
        num_anchors = floor(anchors[index].size() / 2);
        auto both_grids = make_grid(anchors[index], strides[index], outputs_size[index], outputs_size[index], num_anchors);
        xt::xarray<float> grid = std::get<0>(both_grids);
        xt::xarray<float> anchor_grid = std::get<1>(both_grids);
        grids.emplace_back(grid);
        anchor_grids.emplace_back(anchor_grid);
    }
    params->grids = grids;
    params->anchor_grids = anchor_grids;
    params->num_anchors = num_anchors;
    return params;
}

void free_resources(void *params_void_ptr)
{
    Yolov5segParams *params = reinterpret_cast<Yolov5segParams *>(params_void_ptr);
    delete params;
}

/**
 * @brief call the post process and add the detections to the roi
 *
 * @param roi the region of interest
 */
void yolov5seg(HailoROIPtr roi, void *params_void_ptr)
{
    filter(roi, params_void_ptr);
}

/**
 * @brief default filter function
 *
 * @param roi the region of interest
 */
void filter(HailoROIPtr roi, void *params_void_ptr)
{
    Yolov5segParams *params = reinterpret_cast<Yolov5segParams *>(params_void_ptr);
    std::map<std::string, HailoTensorPtr> tensors = roi->get_tensors_by_name();
    std::vector<HailoDetection> detections = yolov5seg_post(tensors, params->anchors, params->strides, params->iou_threshold, params->score_threshold, params->grids, params->anchor_grids, params->num_anchors, params->input_shape[0], params->input_shape[1], params->outputs_name);
    hailo_common::add_detections(roi, detections);
}

void filter_letterbox(HailoROIPtr roi, void *params_void_ptr)
{
    filter(roi, params_void_ptr);
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