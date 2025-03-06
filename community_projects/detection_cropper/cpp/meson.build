
################################################
# detections_cropper SOURCES
################################################

detections_cropper_sources = [
    'detections_cropper.cpp',
]
shared_library('detections_cropper',
    detections_cropper_sources,
    dependencies : postprocess_dep,
    gnu_symbol_visibility : 'default',
    install: true,
    install_dir: join_paths(meson.project_source_root(), 'resources'),
)