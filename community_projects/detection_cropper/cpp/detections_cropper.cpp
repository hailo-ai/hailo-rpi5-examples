/**
* Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
* Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)
**/
#include "detections_cropper.hpp"

#define PERSON_LABEL "person"  //COCO class label: https://docs.ultralytics.com/datasets/detect/coco/

/**
 * @brief Returns a vector of HailoROIPtr to crop and resize.
 *        Specifically, this algorithm doesn't make any actual filter,
 *        it just returns all the available detections
 *
 * @param image The original picture (cv::Mat).
 * @param roi The main ROI of this picture.
 * @return std::vector<HailoROIPtr> vector of ROI's to crop and resize.
 */
std::vector<HailoROIPtr> crop_detections(std::shared_ptr<HailoMat> image, HailoROIPtr roi)
{
    std::vector<HailoROIPtr> crop_rois;
    // Get all detections.
    std::vector<HailoDetectionPtr> detections_ptrs = hailo_common::get_hailo_detections(roi);
    for (HailoDetectionPtr &detection : detections_ptrs)
    {
        if (PERSON_LABEL == detection->get_label())
        {
            crop_rois.emplace_back(detection);
        }
    }
    return crop_rois;
}
