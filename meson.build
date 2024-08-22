project('clip_app', 'cpp',
        version : '1.1.1',
        default_options : ['cpp_std=c++20'])

cpp = meson.get_compiler('cpp')

# Get TAPPAS directories from environment
tappas_workspace = run_command('sh', '-c', 'echo $TAPPAS_WORKSPACE', check: false).stdout().strip()
tappas_post_proc_dir = run_command('sh', '-c', 'echo $TAPPAS_POST_PROC_DIR', check: false).stdout().strip()

# Dependencies
opencv_dep = dependency('opencv4')
gstreamer_dep = dependency('gstreamer-1.0')

rapidjson_dep = dependency('RapidJSON', required: false)
if not rapidjson_dep.found()
  rapidjson_inc = include_directories('/usr/include/rapidjson')
  if not cpp.has_header('rapidjson/document.h', include_directories: rapidjson_inc)
    error('RapidJSON headers not found. Please install rapidjson-dev package.')
  endif
endif

hailo_inc = [
  include_directories('/usr/include/hailo'),
  include_directories('/usr/include/hailo/tappas'),
  include_directories('/usr/lib/aarch64-linux-gnu/hailo/tappas/post-process'),
]
if tappas_workspace != '' and tappas_workspace != '.'
  hailo_inc += include_directories(tappas_workspace)
endif
if tappas_post_proc_dir != '' and tappas_post_proc_dir != '.'
  hailo_inc += include_directories(tappas_post_proc_dir)
endif

# Hailo libraries
hailo_lib_dirs = [
  '/usr/lib',
  '/usr/lib/aarch64-linux-gnu',
  '/usr/lib/aarch64-linux-gnu/hailo/tappas/post-process',
]
if tappas_workspace != '' and tappas_workspace != '.'
  hailo_lib_dirs += [tappas_workspace]
endif
if tappas_post_proc_dir != '' and tappas_post_proc_dir != '.'
  hailo_lib_dirs += [tappas_post_proc_dir]
endif

hailo_lib_names = ['hailort', 'yolo_hailortpp_post']
hailo_libs = []
foreach lib : hailo_lib_names
    hailo_lib = cpp.find_library(lib, dirs: hailo_lib_dirs, required: false)
    if hailo_lib.found()
        hailo_libs += hailo_lib
    else
        warning('Library ' + lib + ' not found. Skipping...')
    endif
endforeach

# Targets
shared_library('yolo_hailortpp_post',
               'cpp/yolo_hailortpp.cpp',
               dependencies: [opencv_dep, gstreamer_dep] + hailo_libs + (rapidjson_dep.found() ? [rapidjson_dep] : []),
               include_directories: hailo_inc + (rapidjson_dep.found() ? [] : [rapidjson_inc]),
               install: true,
               install_dir: 'lib')
