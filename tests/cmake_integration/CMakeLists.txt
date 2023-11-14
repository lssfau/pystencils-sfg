cmake_minimum_required( VERSION 3.24 )

project( pssfg_cmake_integration_test )

set( CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${pssfg_cmake_integration_test_SOURCE_DIR}/../../cmake )

find_package( PystencilsSfg REQUIRED )

add_library( genlib )
pystencilssfg_generate_target_sources( TARGET genlib SCRIPT kernels.py )
