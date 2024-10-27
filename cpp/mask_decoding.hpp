#pragma once

#include "xtensor/xmath.hpp"
#include "xtensor/xadapt.hpp"


/**
 * @brief  Compute sigmoid, not in-place (lazy)
 */
auto xtensor_sigmoid(auto &tensor)
{
    return 1 / (1 + xt::exp(-tensor));
}

/*
 * @brief sigmoid on a single float
 *
 *  */
inline float sigmoid(float x) { return 1.0f / (1.0f + std::exp(-1.0 * x)); }

/**
 * @brief  Compute tensor dot product along specified axes for arrays.
            In this case along axis 2 of the first matrix and axis 0 of the second.
 *
 * @param matrix_1 left matrix in the dot product
 * @param matrix_2 right matrix in the dot product
 * @return xt::xarray<float> the dot product result
 */
xt::xarray<float> dot_product_axis_2(xt::xarray<float, xt::layout_type::row_major> matrix_1,
                                     xt::xarray<float, xt::layout_type::row_major> matrix_2)
{
    uint axis_length = matrix_1.shape(2);
    if (axis_length != matrix_2.shape(0))
    {
        throw std::invalid_argument("dot_product_axis_2 error: axis don't match!");
    }
    float row_sum;
    xt::xarray<float>::shape_type shape = {matrix_1.shape(0), matrix_1.shape(1)};
    xt::xarray<float, xt::layout_type::row_major> product_matrix(shape);
    for (uint i = 0; i < matrix_1.shape(0); ++i)
    {
        for (uint j = 0; j < matrix_1.shape(1); ++j)
        {
            row_sum = 0.0;
            for (uint k = 0; k < axis_length; ++k)
            {
                row_sum += matrix_1(i, j, k) * matrix_2(k);
            }
            product_matrix(i, j) = row_sum;
        }
    }
    return product_matrix;
}

/*
 * @brief Decode the mask coefficients of yolov5seg results into a format that makes sense
 * and add it to the detected instance for future calculation of the final mask
 *
 * @param objects vector of the detected instances
 * @param proto the 32 mask prototypes that the coefficients select portions of to form the mask
 */
void decode_masks(std::vector<HailoDetection> &objects, const xt::xarray<float> &proto)
{
    xt::xarray<float>::shape_type mask_shape = {proto.shape(0), proto.shape(1)};
    int proto_width = proto.shape(0);
    int proto_height = proto.shape(1);
    int xmin, ymin, xmax, ymax;
    for (auto &instance : objects)
    {
        // Gather the detection bounds for this instance,
        // they are relative scale so multiply by proto size
        HailoBBox bbox = instance.get_bbox();
        xmin = CLAMP(bbox.xmin() * proto_width, 0, proto_width);
        xmax = CLAMP(bbox.xmax() * proto_width, 0, proto_width);
        ymin = CLAMP(bbox.ymin() * proto_height, 0, proto_height);
        ymax = CLAMP(bbox.ymax() * proto_height, 0, proto_height);
        // Crop a view of the proto layer of just this instance's detection area
        auto cropped_proto = xt::view(proto, xt::range(ymin, ymax), xt::range(xmin, xmax));
        HailoMatrixPtr matrix = NULL;
        for (auto obj : instance.get_objects())
        {
            if (obj->get_type() == HAILO_MATRIX)
            {
                matrix = std::dynamic_pointer_cast<HailoMatrix>(obj);
            }
        }
        if (matrix == NULL) // no mask attached
        {
            return;
        }
        xt::xarray<int>::shape_type shape = {matrix->height()};
        xt::xarray<float> mask_coefficients = xt::adapt(matrix->get_data().data(), matrix->height(), xt::no_ownership(), shape);

        // Calculate a matrix multiplication of the instance's coefficients and the cropped proto layer and transpose it
        xt::xarray<float, xt::layout_type::column_major> cropped_mask = xt::transpose(dot_product_axis_2(cropped_proto, mask_coefficients));
        instance.remove_object(matrix); // not needed anymore

        // Calculate the sigmoid of the mask
        cropped_mask = xtensor_sigmoid(cropped_mask);

        // allocate and memcpy to a new memory so it points to the right data
        std::vector<float> data(cropped_mask.shape(0) * cropped_mask.shape(1));
        memcpy(data.data(), cropped_mask.data(), sizeof(float) * cropped_mask.shape(0) * cropped_mask.shape(1));
        
        // Add the mask to the object meta
        instance.add_object(std::make_shared<HailoConfClassMask>(std::move(data), cropped_mask.shape(0), cropped_mask.shape(1), 0.3, instance.get_class_id()));
    }
}
