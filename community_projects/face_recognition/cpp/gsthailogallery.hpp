/**
* Copyright (c) 2021-2022 Hailo Technologies Ltd. All rights reserved.
* Distributed under the LGPL license (https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt)
**/
#pragma once
#include <gst/base/gstbasetransform.h>
#include "gallery.hpp"

G_BEGIN_DECLS

#define GST_TYPE_HAILO_GALLERY (gst_hailo_gallery_get_type())
#define GST_HAILO_GALLERY(obj) (G_TYPE_CHECK_INSTANCE_CAST((obj), GST_TYPE_HAILO_GALLERY, GstHailoGallery))
#define GST_HAILO_GALLERY_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST((klass), GST_TYPE_HAILO_GALLERY, GstHailoGalleryClass))
#define GST_IS_HAILO_GALLERY(obj) (G_TYPE_CHECK_INSTANCE_TYPE((obj), GST_TYPE_HAILO_GALLERY))
#define GST_IS_HAILO_GALLERY_CLASS(obj) (G_TYPE_CHECK_CLASS_TYPE((klass), GST_TYPE_HAILO_GALLERY))

typedef struct _GstHailoGallery GstHailoGallery;
typedef struct _GstHailoGalleryClass GstHailoGalleryClass;

struct _GstHailoGallery
{
    GstBaseTransform base_hailogallery;
    gboolean debug;
    gboolean load_gallery;
    gboolean save_gallery;
    gint class_id;
    Gallery gallery;
    gchar *local_gallery_file_path;
};

struct _GstHailoGalleryClass
{
    GstBaseTransformClass base_hailogallery_class;
};

GType gst_hailo_gallery_get_type(void);

G_END_DECLS
