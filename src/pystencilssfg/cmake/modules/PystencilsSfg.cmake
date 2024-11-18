
set(PystencilsSfg_GENERATED_SOURCES_DIR "${CMAKE_BINARY_DIR}/sfg_sources" CACHE PATH "Output directory for genenerated sources" )

mark_as_advanced(PystencilsSfg_GENERATED_SOURCES_DIR)

file(MAKE_DIRECTORY "${PystencilsSfg_GENERATED_SOURCES_DIR}")

function(_pssfg_add_gen_source target script)
    set(options)
    set(oneValueArgs)
    set(multiValueArgs GENERATOR_ARGS DEPENDS)

    cmake_parse_arguments(_pssfg "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    set(generatedSourcesDir ${PystencilsSfg_GENERATED_SOURCES_DIR}/gen/${target})
    get_filename_component(basename ${script} NAME_WLE)
    cmake_path(ABSOLUTE_PATH script OUTPUT_VARIABLE scriptAbsolute)

    execute_process(COMMAND ${Python_EXECUTABLE} -m pystencilssfg list-files "--sep=;" --no-newline ${_pssfg_GENERATOR_ARGS} ${script}
                    OUTPUT_VARIABLE generatedSources RESULT_VARIABLE _pssfg_result
                    ERROR_VARIABLE _pssfg_stderr)

    if(NOT (${_pssfg_result} EQUAL 0))
        message( FATAL_ERROR ${_pssfg_stderr} )
    endif()

    set(generatedSourcesAbsolute)
    foreach (filename ${generatedSources})
        list(APPEND generatedSourcesAbsolute "${generatedSourcesDir}/${filename}")
    endforeach ()

    file(MAKE_DIRECTORY "${generatedSourcesDir}")

    add_custom_command(OUTPUT ${generatedSourcesAbsolute}
                       DEPENDS ${scriptAbsolute} ${_pssfg_DEPENDS}
                       COMMAND ${Python_EXECUTABLE} ${scriptAbsolute} ${_pssfg_GENERATOR_ARGS}
                       WORKING_DIRECTORY "${generatedSourcesDir}")

    target_sources(${target} PRIVATE ${generatedSourcesAbsolute})
    target_include_directories(${target} PRIVATE ${PystencilsSfg_GENERATED_SOURCES_DIR})
endfunction()


function(pystencilssfg_generate_target_sources TARGET)
    set(options)
    set(oneValueArgs OUTPUT_MODE)
    set(multiValueArgs SCRIPTS DEPENDS FILE_EXTENSIONS)
    cmake_parse_arguments(_pssfg "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    set(generatorArgs)

    if(DEFINED _pssfg_OUTPUT_MODE)
        list(APPEND generatorArgs "--sfg-output-mode=${_pssfg_OUTPUT_MODE}")
    endif()

    if(DEFINED PystencilsSfg_CONFIGURATOR_SCRIPT)
        cmake_path(ABSOLUTE_PATH PystencilsSfg_CONFIGURATOR_SCRIPT OUTPUT_VARIABLE configscript)
        list(APPEND generatorArgs "--sfg-config-module=${configscript}")
        list(APPEND _pssfg_DEPENDS ${configscript})
    endif()

    if(DEFINED _pssfg_FILE_EXTENSIONS)
        string(JOIN "," extensionsString ${_pssfg_FILE_EXTENSIONS})

        list(APPEND generatorArgs "--sfg-file-extensions=${extensionsString}")
    endif()

    foreach(codegenScript ${_pssfg_SCRIPTS})
        _pssfg_add_gen_source(${TARGET} ${codegenScript} GENERATOR_ARGS ${generatorArgs} DEPENDS ${_pssfg_DEPENDS})
    endforeach()
    
endfunction()
