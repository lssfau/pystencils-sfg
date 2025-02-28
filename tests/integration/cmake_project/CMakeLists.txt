cmake_minimum_required( VERSION 3.22 )
project( sfg_cmake_project_test )

list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR})

find_package( PystencilsSfg REQUIRED )

if(NOT ${PystencilsSfg_FOUND})
    message( FATAL_ERROR "PystencilsSfg_FOUND was not set even though find_package returned successfully. This is an error." )
endif()

set( UseGlobalCfgModule OFF CACHE BOOL "Specify config module globally" )
set( UseLocalCfgModule OFF CACHE BOOL "Specify config module locally" )

if( $CACHE{UseGlobalCfgModule} )
    set( PystencilsSfg_CONFIG_MODULE ${CMAKE_CURRENT_SOURCE_DIR}/gen_config.py )
endif()

add_executable( TestApp TestApp.cpp )

if( $CACHE{UseLocalCfgModule} )
    pystencilssfg_generate_target_sources(
        TestApp
        SCRIPTS GenTest.py
        CONFIG_MODULE ${CMAKE_CURRENT_SOURCE_DIR}/gen_config.py
    )
else()
    pystencilssfg_generate_target_sources(
        TestApp
        SCRIPTS GenTest.py
    )
endif()

pystencilssfg_generate_target_sources(
    TestApp
    SCRIPTS CliTest.py
    SCRIPT_ARGS apples bananas unicorns
    HEADER_ONLY
)

pystencilssfg_generate_target_sources(
    TestApp
    SCRIPTS CustomDirTest.py
    OUTPUT_DIRECTORY my-output
    HEADER_ONLY
)
