################################################
# FACE ALIGN SOURCES
################################################
face_align_post_sources = [
    'face_align.cpp',
]

shared_library('vms_face_align',
    face_align_post_sources,
    dependencies : postprocess_dep,
    gnu_symbol_visibility : 'default',
    install: true,
    install_dir: join_paths(meson.project_source_root(), 'resources'),
)

################################################
# SCRFD SOURCES
################################################
scrfd_post_sources = [
    'scrfd.cpp',
]

shared_library('scrfd',
    scrfd_post_sources,
    dependencies : postprocess_dep,
    gnu_symbol_visibility : 'default',
    install: true,
    install_dir: join_paths(meson.project_source_root(), 'resources'),
)

################################################
# ARCFACE SOURCES
################################################
arcface_post_sources = [
    'arcface.cpp',
]

shared_library('face_recognition_post',
    arcface_post_sources,
    dependencies : postprocess_dep,
    gnu_symbol_visibility : 'default',
    install: true,
    install_dir: join_paths(meson.project_source_root(), 'resources'),
)

################################################
# VMS CROPPERS SOURCES
################################################
vms_croppers_sources = [
    'vms_croppers.cpp',
]

shared_library('vms_croppers',
    vms_croppers_sources,
    dependencies : postprocess_dep,
    gnu_symbol_visibility : 'default',
    install: true,
    install_dir: join_paths(meson.project_source_root(), 'resources'),
)