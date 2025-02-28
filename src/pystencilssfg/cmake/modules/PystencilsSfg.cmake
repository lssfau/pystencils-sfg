#[[
pystencils-sfg CMake module.

Do not include this module directly; instead use the CMake find-module of pystencils-sfg
to dynamically locate it.
#]]


#   This cache variable definition is a duplicate of the one in FindPystencilsSfg.cmake
if(NOT DEFINED CACHE{PystencilsSfg_PYTHON_INTERPRETER})
    set(PystencilsSfg_PYTHON_INTERPRETER ${Python_EXECUTABLE} CACHE PATH "Path to the Python executable used to run pystencils-sfg")
endif()

if(NOT DEFINED CACHE{_Pystencils_Include_Dir})
    execute_process(
        COMMAND ${PystencilsSfg_PYTHON_INTERPRETER} -c "from pystencils.include import get_pystencils_include_path; print(get_pystencils_include_path(), end='')"
        OUTPUT_VARIABLE _pystencils_includepath_result
    )
    set(_Pystencils_Include_Dir ${_pystencils_includepath_result} CACHE PATH "")
endif()

function(_pssfg_add_gen_source target script outputDirectory)
    set(options)
    set(oneValueArgs)
    set(multiValueArgs GENERATOR_ARGS USER_ARGS DEPENDS)

    cmake_parse_arguments(_pssfg "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    get_filename_component(basename ${script} NAME_WLE)
    cmake_path(ABSOLUTE_PATH script OUTPUT_VARIABLE scriptAbsolute)

    execute_process(COMMAND ${PystencilsSfg_PYTHON_INTERPRETER} -m pystencilssfg list-files "--sep=;" --no-newline ${_pssfg_GENERATOR_ARGS} ${script}
                    OUTPUT_VARIABLE generatedSources RESULT_VARIABLE _pssfg_result
                    ERROR_VARIABLE _pssfg_stderr)

    if(NOT (${_pssfg_result} EQUAL 0))
        message( FATAL_ERROR ${_pssfg_stderr} )
    endif()

    set(generatedSourcesAbsolute)
    foreach (filename ${generatedSources})
        list(APPEND generatedSourcesAbsolute "${outputDirectory}/${filename}")
    endforeach ()

    file(MAKE_DIRECTORY ${outputDirectory})

    add_custom_command(OUTPUT ${generatedSourcesAbsolute}
                       DEPENDS ${scriptAbsolute} ${_pssfg_DEPENDS}
                       COMMAND ${PystencilsSfg_PYTHON_INTERPRETER} ${scriptAbsolute} ${_pssfg_GENERATOR_ARGS} ${_pssfg_USER_ARGS}
                       WORKING_DIRECTORY "${outputDirectory}")

    target_sources(${target} PRIVATE ${generatedSourcesAbsolute})
endfunction()


function(pystencilssfg_generate_target_sources TARGET)
    set(options HEADER_ONLY)
    set(oneValueArgs CONFIG_MODULE OUTPUT_DIRECTORY)
    set(multiValueArgs SCRIPTS DEPENDS FILE_EXTENSIONS SCRIPT_ARGS)
    cmake_parse_arguments(_pssfg "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    set(generatorArgs)

    if(_pssfg_HEADER_ONLY)
        list(APPEND generatorArgs "--sfg-header-only")
    else()
        list(APPEND generatorArgs "--no-sfg-header-only")
    endif()

    if(DEFINED _pssfg_CONFIG_MODULE)
        cmake_path(ABSOLUTE_PATH _pssfg_CONFIG_MODULE OUTPUT_VARIABLE config_module)
        list(APPEND generatorArgs "--sfg-config-module=${config_module}")
        list(APPEND _pssfg_DEPENDS ${config_module})
    else()
        if(DEFINED PystencilsSfg_CONFIGURATOR_SCRIPT)
            message(AUTHOR_WARNING "The variable PystencilsSfg_CONFIGURATOR_SCRIPT is deprecated. Set PystencilsSfg_CONFIG_MODULE instead.")
            cmake_path(ABSOLUTE_PATH PystencilsSfg_CONFIGURATOR_SCRIPT OUTPUT_VARIABLE configscript)
            list(APPEND generatorArgs "--sfg-config-module=${configscript}")
            list(APPEND _pssfg_DEPENDS ${configscript})
        endif()

        if(DEFINED PystencilsSfg_CONFIG_MODULE)
            if(DEFINED PystencilsSfg_CONFIGURATOR_SCRIPT)
                message(FATAL_ERROR "At most one of PystencilsSfg_CONFIGURATOR_SCRIPT and PystencilsSfg_CONFIG_MODULE may be set.")
            endif()

            cmake_path(ABSOLUTE_PATH PystencilsSfg_CONFIG_MODULE OUTPUT_VARIABLE config_module)
            list(APPEND generatorArgs "--sfg-config-module=${config_module}")
            list(APPEND _pssfg_DEPENDS ${config_module})
        endif()
    endif()

    if(DEFINED _pssfg_OUTPUT_DIRECTORY)
        cmake_path(IS_RELATIVE _pssfg_OUTPUT_DIRECTORY _pssfg_output_dir_is_relative)
        if(_pssfg_output_dir_is_relative)
            set(outputDirectory ${CMAKE_CURRENT_BINARY_DIR}/${_pssfg_OUTPUT_DIRECTORY})
        else()
            set(outputDirectory ${_pssfg_OUTPUT_DIRECTORY})
        endif()
    else()
        set(generatedSourcesIncludeDir ${CMAKE_CURRENT_BINARY_DIR}/_gen/${TARGET})
        set(outputDirectory ${generatedSourcesIncludeDir}/gen)
        target_include_directories(${TARGET} PRIVATE ${generatedSourcesIncludeDir})
    endif()

    if(DEFINED _pssfg_FILE_EXTENSIONS)
        string(JOIN "," extensionsString ${_pssfg_FILE_EXTENSIONS})

        list(APPEND generatorArgs "--sfg-file-extensions=${extensionsString}")
    endif()

    if(DEFINED _pssfg_SCRIPT_ARGS)
        #   User has provided custom command line arguments
        set(userArgs ${_pssfg_SCRIPT_ARGS})
    endif()

    foreach(codegenScript ${_pssfg_SCRIPTS})
        _pssfg_add_gen_source(
            ${TARGET} ${codegenScript} ${outputDirectory}
            GENERATOR_ARGS ${generatorArgs}
            USER_ARGS ${userArgs}
            DEPENDS ${_pssfg_DEPENDS}
        )
    endforeach()

    target_include_directories(${TARGET} PRIVATE ${_Pystencils_Include_Dir})
    
endfunction()
