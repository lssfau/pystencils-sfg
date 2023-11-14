
set(PSSFG_GENERATED_SOURCES_DIR "${CMAKE_BINARY_DIR}/pystencils_generated_sources")
file(MAKE_DIRECTORY "${PSSFG_GENERATED_SOURCES_DIR}")
include_directories(${PSSFG_GENERATED_SOURCES_DIR})

function(pystencilssfg_generate_target_sources)
    set(options)
    set(oneValueArgs TARGET SCRIPT)
    set(multiValueArgs DEPENDS)
    cmake_parse_arguments(GENSRC "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    set(generatedSourcesDir ${PSSFG_GENERATED_SOURCES_DIR}/gen/${GENSRC_TARGET})

    get_filename_component(basename ${GENSRC_SCRIPT} NAME_WLE)
    cmake_path(ABSOLUTE_PATH GENSRC_SCRIPT OUTPUT_VARIABLE pythonFile)

    set(generatedSourceFiles ${basename}.h ${basename}.cpp)
    set(generatedWithAbsolutePath)
    foreach (filename ${generatedSourceFiles})
        list(APPEND generatedWithAbsolutePath ${generatedSourcesDir}/${filename})
    endforeach ()

    file(MAKE_DIRECTORY "${generatedSourcesDir}")

    # TODO: Get generator arguments via PYSTENCILS_GENERATOR_FLAGS, source file and target properties

    add_custom_command(OUTPUT ${generatedWithAbsolutePath}
            DEPENDS ${pythonFile} ${GENSRC_DEPENDS}
            COMMAND ${Python_EXECUTABLE} ${pythonFile}
            WORKING_DIRECTORY "${generatedSourcesDir}")

    target_sources(${GENSRC_TARGET} PRIVATE ${generatedWithAbsolutePath})
endfunction()
