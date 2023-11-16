
set(PSSFG_CONFIGURATOR_SCRIPT "" CACHE FILEPATH "Configurator script for the pystencils Source File Generator" )

set(PSSFG_GENERATED_SOURCES_DIR "${CMAKE_BINARY_DIR}/pystencils_generated_sources")
file(MAKE_DIRECTORY "${PSSFG_GENERATED_SOURCES_DIR}")
include_directories(${PSSFG_GENERATED_SOURCES_DIR})


function(_pssfg_add_gen_source target script)
    set(options)
    set(oneValueArgs)
    set(multiValueArgs GENERATOR_ARGS DEPENDS)

    cmake_parse_arguments(_pssfg "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    set(generatedSourcesDir ${PSSFG_GENERATED_SOURCES_DIR}/gen/${target})
    get_filename_component(basename ${script} NAME_WLE)
    cmake_path(ABSOLUTE_PATH script OUTPUT_VARIABLE scriptAbsolute)

    execute_process(COMMAND ${Python_EXECUTABLE} -m pystencilssfg list-files --format=cmake ${_pssfg_GENERATOR_ARGS} ${script}
                    OUTPUT_VARIABLE generatedSources RESULT_VARIABLE _pssfg_result
                    ERROR_VARIABLE _pssfg_stderr)

    if(NOT (${_pssfg_result} EQUAL 0))
        message( FATAL_ERROR ${_pssfg_stderr} )
    endif()

    set(generatedSourcesAbsolute)
    foreach (filename ${generatedSources})
        list(APPEND generatedSourcesAbsolute ${generatedSourcesDir}/${filename})
    endforeach ()

    file(MAKE_DIRECTORY "${generatedSourcesDir}")

    add_custom_command(OUTPUT ${generatedSourcesAbsolute}
                       DEPENDS ${scriptAbsolute} ${_pssfg_DEPENDS}
                       COMMAND ${Python_EXECUTABLE} ${scriptAbsolute} ${_pssfg_GENERATOR_ARGS}
                       WORKING_DIRECTORY "${generatedSourcesDir}")

    target_sources(${target} PRIVATE ${generatedSourcesAbsolute})
endfunction()


function(pystencilssfg_generate_target_sources TARGET)
    set(options HEADER_ONLY)
    set(multiValueArgs SCRIPTS DEPENDS FILE_EXTENSIONS)
    cmake_parse_arguments(_pssfg "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    set(generatedSourcesDir ${PSSFG_GENERATED_SOURCES_DIR}/gen/${_pssfg_TARGET})

    set(generatorArgs)

    if(_pssfg_HEADER_ONLY)
        list(APPEND generatorArgs "--sfg-header-only")
    endif()

    if(NOT (PSSFG_CONFIGURATOR_SCRIPT STREQUAL ""))
        list(APPEND generatorArgs "--sfg-configurator='${_pssfg_CONFIGURATOR_SCRIPT}'")
    endif()

    if(DEFINED _pssfg_FILE_EXTENSIONS)
        string(JOIN "," extensionsString ${_pssfg_FILE_EXTENSIONS})

        list(APPEND generatorArgs "--sfg-file-extensions=${extensionsString}")
    endif()

    foreach(codegenScript ${_pssfg_SCRIPTS})
        _pssfg_add_gen_source(${TARGET} ${codegenScript} GENERATOR_ARGS ${generatorArgs} DEPENDS ${_pssfg_DEPENDS})
    endforeach()
    
endfunction()
