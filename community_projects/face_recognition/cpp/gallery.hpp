/**
 * Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
 * Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)
 **/
#pragma once
#include <vector>
#include <cstdio>
#include <string>
#include <ostream>
#include <filesystem>
#include "xtensor/xarray.hpp"
#include "xtensor/xadapt.hpp"
#include "xtensor/xsort.hpp"
#include "xtensor/xio.hpp"
#include "hailo_objects.hpp"
#include "export/encode_json.hpp"
#include "import/decode_json.hpp"

#define RAPIDJSON_HAS_STDSTRING 1
#include "rapidjson/document.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/error/en.h"
#include "rapidjson/filewritestream.h"
#include "rapidjson/writer.h"
#include "rapidjson/prettywriter.h"

static xt::xarray<float> gallery_get_xtensor(HailoMatrixPtr matrix)
{
    // Adapt a HailoTensorPtr to an xarray (quantized)
    xt::xarray<float> xtensor = xt::adapt(matrix->get_data().data(), matrix->size(), xt::no_ownership(), matrix->shape());
    return xt::squeeze(xtensor);
}

static float gallery_one_dim_dot_product(xt::xarray<float> array1, xt::xarray<float> array2)
{
    if (array1.dimension() > 1 || array2.dimension() > 1)
    {
        throw std::runtime_error("One of the arrays has more than 1 dimension");
    }
    if (array1.shape(0) != array2.shape(0))
    {
        throw std::runtime_error("Arrays are with different shape");
    }
    return xt::sum(array1 * array2)[0];
}

class Gallery
{
private:
    // Each embedding is represented by HailoMatrixPtr
    // Each global_id has a vector of embeddings (I.e. vector of HailoMatrixPtr)
    // of all the embeddings related to this ID.
    // For the whole gallery there is a vector of global id's (i.e. vector of vectors of HailoMatrixPtr)
    // where the global ID is represented by the outer vector's index.
    std::vector<std::vector<HailoMatrixPtr>> m_embeddings;
    std::map<int, int> tracking_id_to_global_id;
    std::vector<std::string> m_embedding_names;
    float m_similarity_thr;
    uint m_queue_size;
    FILE *m_json_file;
    bool m_save_new_embeddings;
    char *m_json_file_path;
    bool m_load_local_embeddings;

public:
    Gallery(float similarity_thr = 0.15, uint queue_size = 100) : m_similarity_thr(similarity_thr), m_queue_size(queue_size),
                                                                  m_json_file(nullptr), m_save_new_embeddings(false),
                                                                  m_json_file_path(nullptr), m_load_local_embeddings(false){};

    static float get_distance(std::vector<HailoMatrixPtr> embeddings_queue, HailoMatrixPtr matrix)
    {
        xt::xarray<float> new_embedding = gallery_get_xtensor(matrix);
        float max_thr = 0.0f;
        float thr;
        for (HailoMatrixPtr embedding_mat : embeddings_queue)
        {
            xt::xarray<float> embedding = gallery_get_xtensor(embedding_mat);
            thr = gallery_one_dim_dot_product(embedding, new_embedding);
            max_thr = thr > max_thr ? thr : max_thr;
        }
        return 1.0f - max_thr;
    }

    xt::xarray<float> get_embeddings_distances(HailoMatrixPtr matrix)
    {
        std::vector<float> distances;
        for (auto embeddings_queue : m_embeddings)
        {
            distances.push_back(get_distance(embeddings_queue, matrix));
        }
        return xt::adapt(distances);
    }

    void init_local_gallery_file(const char *file_path)
    {
        if (!std::filesystem::exists(file_path))
        {
            this->m_json_file = fopen(file_path, "w");
            fputs("[]", this->m_json_file);
            fclose(this->m_json_file);
            this->m_json_file = nullptr;
        }

        this->m_json_file_path = strdup(file_path);
        this->m_save_new_embeddings = true;
    }

    void load_local_gallery_from_json(const char *file_path)
    {
        if (!std::filesystem::exists(file_path))
            throw std::runtime_error("Gallery JSON file does not exist");

        this->m_json_file = fopen(file_path, "r");
        if (this->m_json_file == nullptr)
            throw std::runtime_error("Gallery JSON file is not valid");

        this->m_json_file_path = strdup(file_path);

        char read_buffer[4096];
        HailoROIPtr roi = std::make_shared<HailoROI>(HailoROI(HailoBBox(0.0f, 0.0f, 1.0f, 1.0f)));
        rapidjson::FileReadStream stream(this->m_json_file, read_buffer, sizeof(read_buffer));
        rapidjson::Document doc_config_json;
        doc_config_json.ParseStream(stream);

        decode_json::decode_hailo_face_recognition_result(doc_config_json.GetArray(), roi, this->m_embedding_names);
        this->m_load_local_embeddings = true;

        auto matrix_objs = roi->get_objects_typed(HAILO_MATRIX);
        for (auto matrix : matrix_objs)
        {
            HailoMatrixPtr matrix_ptr = std::dynamic_pointer_cast<HailoMatrix>(matrix);
            uint global_id = create_new_global_id();
            add_embedding(global_id, matrix_ptr);
        }

        fclose(this->m_json_file);
        this->m_json_file = nullptr;
    }

    void add_embedding(uint global_id, HailoMatrixPtr matrix)
    {
        global_id--;
        if (m_embeddings[global_id].size() >= m_queue_size)
        {
            m_embeddings[global_id].pop_back();
        }
        m_embeddings[global_id].insert(m_embeddings[global_id].begin(), matrix);
    }

    void write_to_json_file(rapidjson::Document document)
    {
        // Open the file
        this->m_json_file = fopen(this->m_json_file_path, "rb+");

        // Replace the "]" terminator with "," (if not empty)
        if (std::getc(this->m_json_file) == '[' && std::getc(this->m_json_file) != ']')
        {
            std::fseek(this->m_json_file, -1, SEEK_END);
            std::fputc(',', this->m_json_file);
        }
        else
        {
            std::fseek(this->m_json_file, -1, SEEK_END);
        }

        // Append the new entry to the document
        char writeBuffer[65536];
        rapidjson::FileWriteStream write_stream(this->m_json_file, writeBuffer, sizeof(writeBuffer));
        rapidjson::PrettyWriter<rapidjson::FileWriteStream> writer(write_stream);
        document.Accept(writer);

        // Close the array
        std::fputc(']', this->m_json_file);
        fclose(this->m_json_file);
        this->m_json_file = nullptr;
    }

    void save_embedding_to_json_file(HailoMatrixPtr matrix, const uint global_id)
    {
        if (this->m_save_new_embeddings)
        {
            std::string name = "Unknown" + std::to_string(global_id);
            write_to_json_file(encode_json::encode_hailo_face_recognition_result(matrix, name.c_str()));
        }
    }

    uint create_new_global_id()
    {
        std::vector<HailoMatrixPtr> queue;
        m_embeddings.push_back(queue);
        uint global_id = m_embeddings.size();
        return global_id;
    }

    std::pair<uint, float> get_closest_global_id(HailoMatrixPtr matrix)
    {
        auto distances = get_embeddings_distances(matrix);
        auto global_id = xt::argpartition(distances, 1, xt::xnone())[0];
        return std::pair<uint, float>(global_id + 1, distances[global_id]);
    }

    HailoMatrixPtr get_embedding_matrix(HailoDetectionPtr detection)
    {
        auto embeddings = detection->get_objects_typed(HAILO_MATRIX);
        if (embeddings.size() == 0)
        {
            // No HailoMatrix, continue to next detection.
            return nullptr;
        }
        else if (embeddings.size() > 1)
        {
            // More than 1 HailoMatrixPtr is not allowed.
            std::runtime_error("A detection has more than 1 HailoMatrixPtr");
        }
        return std::dynamic_pointer_cast<HailoMatrix>(embeddings[0]);
    }

    void handle_local_embedding(HailoDetectionPtr detection, const uint global_id)
    {
        if ((global_id - 1) < this->m_embedding_names.size())
        {
            // Embedding found and matches a name, add it as a classifcation object.
            std::string classification_type = "recognition_result";
            auto existing_recognitions = hailo_common::get_hailo_classifications(detection, classification_type);
            if (existing_recognitions.size() == 0 ||  existing_recognitions[0]->get_classification_type() != classification_type)
            {
                detection->add_object(std::make_shared<HailoClassification>(classification_type, this->m_embedding_names[global_id - 1]));
            }
        }
    }

    void update_embeddings_and_add_id_to_object(HailoMatrixPtr new_embedding, HailoDetectionPtr detection, const uint global_id, const int unique_id)
    {
        // Attach global id to tracking id
        tracking_id_to_global_id[unique_id] = global_id;

        // Add new embedding to the queue
        if (!this->m_load_local_embeddings && new_embedding != nullptr)
            add_embedding(global_id, new_embedding);

        // Add global id to detection.
        auto global_ids = hailo_common::get_hailo_global_id(detection);
        if (global_ids.size() == 0)
            detection->add_object(std::make_shared<HailoUniqueID>(global_id, GLOBAL_ID));
    }

    void new_embedding_to_global_id(HailoMatrixPtr new_embedding, HailoDetectionPtr detection, const int track_id)
    {
        if (tracking_id_to_global_id.find(track_id) != tracking_id_to_global_id.end())
        {
            // Global id to track already exists, add new embedding to global id
            update_embeddings_and_add_id_to_object(new_embedding, detection, tracking_id_to_global_id[track_id], track_id);
            if (this->m_load_local_embeddings)
                handle_local_embedding(detection, tracking_id_to_global_id[track_id]);
            return;
        }

        if (new_embedding == nullptr)
        {
            // No embedding exists in this detection object, continue to next detection
            return;
        }

        if (m_embeddings.empty())
        {
            // Gallery is empty, adding new global id
            uint global_id = create_new_global_id();
            save_embedding_to_json_file(new_embedding, global_id);
            update_embeddings_and_add_id_to_object(new_embedding, detection, global_id, track_id);
            return;
        }

        uint closest_global_id;
        float min_distance;
        // Get closest global id by distance between embeddings
        std::tie(closest_global_id, min_distance) = get_closest_global_id(new_embedding);
        if (min_distance > this->m_similarity_thr)
        {
            // if smallest distance is bigger than threshold and local gallery is not loaded -> create new global ID
            if (!this->m_load_local_embeddings)
            {
                uint global_id = create_new_global_id();
                save_embedding_to_json_file(new_embedding, global_id);
                update_embeddings_and_add_id_to_object(new_embedding, detection, global_id, track_id);
            }
        }
        else
        {
            // Close embedding found, update global id embeddings
            update_embeddings_and_add_id_to_object(new_embedding, detection, closest_global_id, track_id);
            if (this->m_load_local_embeddings)
                handle_local_embedding(detection, closest_global_id);
        }
    }

    void update(std::vector<HailoDetectionPtr> &detections)
    {
        for (auto detection : detections)
        {
            auto track_ids = hailo_common::get_hailo_track_id(detection);
            int track_id = std::dynamic_pointer_cast<HailoUniqueID>(track_ids[0])->get_id();

            HailoMatrixPtr new_embedding = get_embedding_matrix(detection);
            new_embedding_to_global_id(new_embedding, detection, track_id);
        }
    };
    void set_similarity_threshold(float thr) { this->m_similarity_thr = thr; };
    void set_queue_size(uint size) { m_queue_size = size; };
    float get_similarity_threshold() { return m_similarity_thr; };
    uint get_queue_size() { return m_queue_size; };
};
