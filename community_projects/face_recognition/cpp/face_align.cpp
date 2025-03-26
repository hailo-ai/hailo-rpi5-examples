/**
 * Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
 * Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)
 **/

#include <gst/video/video.h>

// Hailo includes
#include "face_align.hpp"
#include "hailo_common.hpp"
#include "image.hpp"

// Open source includes
#include <opencv2/opencv.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/core.hpp>

std::vector<float> DEST_VECTOR{38.2946f, 51.6963f,
                               73.5318f, 51.5014f,
                               56.0252f, 71.7366f,
                               41.5493f, 92.3655f,
                               70.7299f, 92.2041f};

cv::Mat DEST_MATRIX(5, 2, cv::DataType<float>::type, DEST_VECTOR.data());


/**
 * @brief Get the face landmarks from the ROI
 * Aling the points of the landmarks object to the given dimensions.
 *
 * @param height guint height to align to
 * @param width guint width to align to
 * @param roi the region of interest
 * @return cv::Mat contains the aligned landmarks
 */
cv::Mat get_landmarks(guint width, guint height, HailoROIPtr roi)
{
    cv::Mat landmarks(5, 2, cv::DataType<float>::type);
    auto landmarks_objects = roi->get_objects_typed(HAILO_LANDMARKS);

    if (landmarks_objects.empty())
    {
        GST_WARNING("There are no landmarks in buffer");
    }
    else if (landmarks_objects.size() > 1)
    {
        GST_WARNING("Too many landmarks");
    }
    else
    {
        HailoLandmarksPtr landmarks_obj = std::dynamic_pointer_cast<HailoLandmarks>(landmarks_objects[0]);
        std::vector<HailoPoint> points = landmarks_obj->get_points();

        for (size_t i = 0; i < points.size(); i++)
        {
            float x = points[i].x() * width;
            float y = points[i].y() * height;

            landmarks.at<float>(i, 0) = x;
            landmarks.at<float>(i, 1) = y;
        }
    }
    return landmarks;
}


/**
 * @brief Generate and return transformation/'warp' matrix, using the Roi's landmarks and the destination matrix.
 * The transformation matrix is used later to warp the image.
 * 
 * @param width guint width of the image
 * @param height guint height of the image
 * @param roi HailoRoiPtr
 * @return cv::Mat transformation matrix
 */
cv::Mat generate_warp_matrix_from_roi(guint width, guint height , HailoROIPtr roi)
{
    // Get the landmarks from the ROI
    auto landmarks = get_landmarks(width, height, roi);

    // Perform similarity transform between the landmarks and the destination matrix
    auto warp_mat = FacePreprocess::similarTransform(landmarks, DEST_MATRIX);
    warp_mat = warp_mat.rowRange(0, 2);

    return warp_mat;
}

void filter(HailoROIPtr roi, GstVideoFrame *frame, gchar *current_stream_id)
{
    // Get the CV::Mat from the GstVideoFrame
    cv::Mat image = get_mat_from_gst_frame(frame);

    guint width = image.cols;
    guint height = image.rows;

    cv::Mat img;
    GstVideoInfo *info = &frame->info;
    switch (info->finfo->format)
    {
    case GST_VIDEO_FORMAT_RGBA:
    case GST_VIDEO_FORMAT_RGB:
    {
        cv::Mat warp_mat = generate_warp_matrix_from_roi(width, height, roi);
         // Warp the image matrix by Affine transformation
        cv::warpAffine(image, image, warp_mat, image.size());
        break;
    }
    case GST_VIDEO_FORMAT_NV12:
    {
        // Split the nv12 mat into Y and UV mats
        cv::Mat y_mat = cv::Mat(height * 2 / 3, width, CV_8UC1, (char *)image.data, width);
        cv::Mat uv_mat = cv::Mat(height / 3, width / 2, CV_8UC2, (char *)image.data + ((height*2/3)*width), width);

        cv::Mat warp_mat = generate_warp_matrix_from_roi(y_mat.cols, y_mat.rows, roi);
        // Warp the Y matrix by Affine transformation
        cv::warpAffine(y_mat, y_mat, warp_mat, y_mat.size());

        // Warp the UV matrix by Affine transformation
        warp_mat.at<float>(0, 2) = warp_mat.at<float>(0, 2) / 2;
        warp_mat.at<float>(1, 2) = warp_mat.at<float>(1, 2) / 2;
        cv::warpAffine(uv_mat, uv_mat, warp_mat, uv_mat.size(), cv::INTER_LINEAR);
        break;
    }
    default:
        GST_ERROR("Unsupported format");
        return;
    }

}