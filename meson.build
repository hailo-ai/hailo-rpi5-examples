project('hailo_rpi5_examples', 'c', 'cpp',
        version : '1.1.1',
        default_options : [ 'warning_level=1',
                            'buildtype=release',
                            'c_std=c11', 'cpp_std=c++17',
                            'c_args=-Wno-psabi',
                            'cpp_args=-Wno-psabi -Wno-class-memaccess -Wno-deprecated-declarations']
       )

postprocess_dep = dependency('hailo-tappas-core', version : '>=3.30.0', required : false)

if not postprocess_dep.found()
    postprocess_dep = dependency('hailo_tappas', version : '>=3.30.0')
endif

# Use the rapidjson_includedir from the pkg-config file
rapidjson_inc_dir = postprocess_dep.get_variable(pkgconfig: 'rapidjson_includedir')

# rapidjson Include Directories
rapidjson_inc = include_directories(rapidjson_inc_dir, is_system: true)

subdir('cpp')
