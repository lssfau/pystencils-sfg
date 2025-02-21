cmake_minimum_required( VERSION 3.24 )
project(PystencilsSfg_Standalone)

if (DEFINED CACHE{PystencilsSfg_PYTHON_INTERPRETER})
    set( _use_venv_init OFF)
elseif(DEFINED PystencilsSfg_PYTHON_PATH)
    set( _use_venv_init OFF)
else()
    set( _use_venv_init ON )
endif()

set(CODEGEN_PRIVATE_VENV ${_use_venv_init}
    CACHE BOOL
    "Create a private virtual Python environment inside the build tree for code generation"
)

function(codegen_venv_install)
    if(NOT CODEGEN_PRIVATE_VENV)
        return()
    endif()

    if(NOT _sfg_private_venv_done)
        message( FATAL_ERROR "The private virtual environment for code generation was not initialized yet" )
    endif()

    execute_process(
	COMMAND ${PystencilsSfg_PYTHON_INTERPRETER} -m pip install ${ARGV}
    )
endfunction()


if (CODEGEN_PRIVATE_VENV)

	set(CODEGEN_VENV_PATH ${CMAKE_CURRENT_BINARY_DIR}/codegen-venv CACHE PATH "Location of the virtual environment used for code generation")
	set(_venv_python_exe ${CODEGEN_VENV_PATH}/bin/python)
	set(CODEGEN_VENV_PYTHON ${_venv_python_exe})

	find_package( Python COMPONENTS Interpreter REQUIRED )

	if(NOT _sfg_private_venv_done)
		message( STATUS "Setting up Python virtual environment at ${CODEGEN_VENV_PATH}" )

		#   Create the venv and register its interpreter with pystencils-sfg
		if(NOT EXISTS ${CODEGEN_VENV_PATH})
			execute_process( COMMAND ${Python_EXECUTABLE} -m venv ${CODEGEN_VENV_PATH})
		endif()


		set(CODEGEN_VENV_REQUIREMENTS ${PROJECT_SOURCE_DIR}/requirements.txt CACHE FILEPATH "Location of the requirements installed in the virtual environment used for code generation")
		if (EXISTS ${CODEGEN_VENV_REQUIREMENTS})
			message( STATUS "Installing required Python packages from ${CODEGEN_VENV_REQUIREMENTS}" )
			execute_process( COMMAND ${_venv_python_exe} -m pip install -r ${CODEGEN_VENV_REQUIREMENTS} OUTPUT_QUIET)
		else()
			message( WARNING "Could not find ${CODEGEN_VENV_REQUIREMENTS}" )
		endif()

		set( _sfg_private_venv_done TRUE CACHE BOOL "" )
		mark_as_advanced(_sfg_private_venv_done)
	endif()
	set(_sfg_cache_python_init ${_venv_python_exe})
	set(PystencilsSfg_PYTHON_INTERPRETER ${_sfg_cache_python_init} CACHE PATH "Path to the Python executable used to run pystencils-sfg")
endif()

# get the find pystencils-sfg file
execute_process( 
	COMMAND ${PystencilsSfg_PYTHON_INTERPRETER} -m pystencilssfg cmake make-find-module
	WORKING_DIRECTORY ${CMAKE_FIND_PACKAGE_REDIRECTS_DIR}
)
# renaming it
file(RENAME ${CMAKE_FIND_PACKAGE_REDIRECTS_DIR}/FindPystencilsSfg.cmake ${CMAKE_FIND_PACKAGE_REDIRECTS_DIR}/pystencilssfg-config.cmake)

# Find it
find_package( PystencilsSfg REQUIRED )
