cmake_minimum_required( VERSION 3.24 )

project( pssfg_cmake_integration_test )

set( CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${pssfg_cmake_integration_test_SOURCE_DIR}/.cmake )

#   Don't try this at home!
file(MAKE_DIRECTORY .cmake)
execute_process( COMMAND sfg-cli cmake make-find-module
                 WORKING_DIRECTORY ${pssfg_cmake_integration_test_SOURCE_DIR}/.cmake )

find_package( PystencilsSfg REQUIRED )

set( PystencilsSfg_CONFIGURATOR_SCRIPT codegen_config.py )

add_library( genlib )
pystencilssfg_generate_target_sources( genlib SCRIPTS kernels.py FILE_EXTENSIONS .h .cpp )
pystencilssfg_generate_target_sources( genlib SCRIPTS more_kernels.py )
