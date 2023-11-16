set( PystencilsSfg_FOUND OFF CACHE BOOL "pystencils source file generator found" )

mark_as_advanced( PystencilsSfg_FOUND )

find_package( Python COMPONENTS Interpreter REQUIRED )

#   Try to find pystencils-sfg in the python environment

execute_process(COMMAND ${Python_EXECUTABLE} -c "import pystencilssfg; print(pystencilssfg.__version__, end='')"
                RESULT_VARIABLE _PystencilsSfgFindResult OUTPUT_VARIABLE PystencilsSfg_VERSION )

if(${_PystencilsSfgFindResult} EQUAL 0)
    set( PystencilsSfg_FOUND ON )
endif()

if(${PystencilsSfg_FIND_REQUIRED} AND (NOT ${PystencilsSfg_FOUND}))
    message( FATAL_ERROR "Could not find pystencils-sfg in current Python environment." )
endif()

if(${PystencilsSfg_FOUND})
    message( STATUS "Found pystencils Source File Generator (Version ${PystencilsSfg_VERSION})")
    
    execute_process(COMMAND ${Python_EXECUTABLE} -c "from pystencilssfg.cmake import get_sfg_cmake_modulepath; print(get_sfg_cmake_modulepath(), end='')"
                    OUTPUT_VARIABLE _PystencilsSfg_CMAKE_MODULE_PATH)

    set( CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${_PystencilsSfg_CMAKE_MODULE_PATH})
    include( PystencilsSfgFunctions )
endif()

