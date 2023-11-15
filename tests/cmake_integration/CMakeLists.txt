cmake_minimum_required( VERSION 3.24 )

project( pssfg_cmake_integration_test )

set( CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${pssfg_cmake_integration_test_SOURCE_DIR}/../../cmake )

find_package( PystencilsSfg REQUIRED )

# set( PSSFG_CONFIGURATOR_SCRIPT "codegen_config.py" )

add_library( genlib )
pystencilssfg_generate_target_sources( genlib SCRIPTS kernels.py more_kernels.py FILE_EXTENSIONS .hpp .cpp )
