
################################################
# YOLO HAILORTPP POST SOURCES
################################################

yolo_hailortpp_sources = [
    'yolo_hailortpp.cpp'
]
shared_library('yolo_hailortpp_postprocess',
    yolo_hailortpp_sources,
    include_directories : rapidjson_inc,
    dependencies : postprocess_dep,
    gnu_symbol_visibility : 'default',
    install: true,
    install_dir: join_paths(meson.project_source_root(), 'resources'),
)
################################################
# REMOVE LABELS POST SOURCES
################################################

remove_labels_sources = [
    'remove_labels.cpp',
]
shared_library('remove_labels',
    remove_labels_sources,
    dependencies : postprocess_dep,
    gnu_symbol_visibility : 'default',
    install: true,
    install_dir: join_paths(meson.project_source_root(), 'resources'),
)

################################################
# yolov8pose_postprocess SOURCES
################################################

yolov8pose_postprocess_sources = [
    'yolov8pose_postprocess.cpp',
]
shared_library('yolov8pose_postprocess',
    yolov8pose_postprocess_sources,
    dependencies : postprocess_dep,
    gnu_symbol_visibility : 'default',
    install: true,
    install_dir: join_paths(meson.project_source_root(), 'resources'),
)

################################################
# YOLOV5SEG SOURCES
################################################
yolov5seg_post_sources = [
    'yolov5seg.cpp',
]

shared_library('yolov5seg_postprocess',
    yolov5seg_post_sources,
    dependencies : postprocess_dep,
    gnu_symbol_visibility : 'default',
    install: true,
    install_dir: join_paths(meson.project_source_root(), 'resources'),
)