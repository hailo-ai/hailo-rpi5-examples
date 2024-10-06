/**
 * Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
 * Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)
 **/
#include <iostream>
#include <set>
#include <fstream>
#include "remove_labels.hpp"

#if __GNUC__ > 8
#include <filesystem>
namespace fs = std::filesystem;
#else
#include <experimental/filesystem>
namespace fs = std::experimental::filesystem;
#endif

/**
 * @brief Filters out specified labels from the frame metadata.
 *
 * This filter reads a text file from the config_path parameter. Each line in the file
 * should describe a label to be removed from the frame metadata. The labels are stored
 * in a set and used to filter out detections that match any of the specified labels.
 *
 * @param config_path The path to the text file containing labels to remove, one per line.
 *
 * @return A pointer to a LabelsParams object containing the labels to be removed.
 *
 * @note Ensure that the text file is formatted correctly, with one label per line.
 *       Any empty lines or lines with only whitespace will be ignored.
 *
 * @example
 * To use this filter, create a text file named "labels_to_remove.txt" with the following content:
 * person
 * car
 * tv
 *
 * To add this filter to your pipeline, you would typically include the following in your code:
 * remover_so_path = os.path.join(self.current_path, '../resources/libremove_labels.so')
 * # adjust the path to the labels_to_remove.txt file
 * labels_to_remove_path = os.path.join(self.current_path, '../resources/labels_to_remove.txt')
 * 'hailofilter name=remover so-path=remover_so_path config-path=labels_to_remove_path qos=false ! '
 */

LabelsParams *init(const std::string config_path, const std::string function_name)
{
    std::set<std::string> labels_to_remove;
    std::ifstream file(config_path);
    std::string line;

    while (std::getline(file, line))
    {
        labels_to_remove.insert(line);
        std::cout << "Label to remove: " << line << std::endl;
    }

    LabelsParams *params = new LabelsParams(std::move(labels_to_remove));
    return params;
}

void filter(HailoROIPtr roi, void *params_void_ptr)
{
    LabelsParams *params = reinterpret_cast<LabelsParams *>(params_void_ptr);
    auto detections = hailo_common::get_hailo_detections(roi);
    for (const auto &detection : detections)
    {
        if (params->labels_to_remove.find(detection->get_label()) != params->labels_to_remove.end())
        {
            roi->remove_object(detection);
        }
    }
}