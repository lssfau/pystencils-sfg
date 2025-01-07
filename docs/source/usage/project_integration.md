(guide_project_integration)=
# Project and Build System Integration

(config_module)=
## Project-Wide Settings using Configuration Modules

When embedding *pystencils-sfg* into a C++ project or build system,
you might want to set a project-wide base configuration for all generator scripts.
In addition, it might be necessary to pass various details about the project
and build setup to the generator scripts.
Both can be achieved by the use of a *configuration module*.

A configuration module is a Python file that defines up to two functions:
- `def configure_sfg(cfg: SfgConfig)` is called to set up the project-wide base configuration.
   It takes an {any}`SfgConfig` object which it may modify to establish the project-wide option set.
- `def project_info() -> Any` is called by *pystencils-sfg* to retrieve an object that encapsulates
  any custom project-specific information.
  This information is passed on to the generator scripts through
  the {any}`sfg.context.project_info <SfgContext.project_info>` attribute.

An example configuration module might look like this:

```Python
from pystencilssfg import SfgConfig

def configure_sfg(cfg: SfgConfig):
    cfg.extensions.header = "h++"
    cfg.extensions.impl = "c++"
    cfg.clang_format.code_style = "llvm"
    ...

def project_info():
    return {
        "project_name": "my-project",
        "float_precision": "float32",
        "use_cuda": False,
        ...
    }
```

Here, `project_info` returns a dictionary, but this is just for illustration;
the function may return any type of arbitrarily complex objects.
For improved API safety, {any}`dataclasses` might be a good tool for setting up
project info objects.

When invoking a generator script, the path to the current configuration module must be passed to it
using the `--sfg-config-module` command-line parameter.
This can be automated by an adequately set up build system, such as GNU Make or CMake.

If you are using pystencils-sfg with CMake through the provided CMake module,
[see below](#cmake_set_config_module) on how to specify a configuration module for your project.

(cmake_integration)=
## CMake Integration

*pystencils-sfg* is shipped with a CMake module for on-the-fly code generation during the CMake build process.

### Add the module

To include the module in your CMake source tree, a separate find module is provided.
You can use the global CLI to obtain the find module; simply run

```shell
sfg-cli cmake make-find-module
```

to create the file `FindPystencilsSfg.cmake` in the current directory.
Add it to the CMake module path, and load the *pystencils-sfg* module via *find_package*:

```CMake
find_package( PystencilsSfg )
```

Make sure to set the `Python_ROOT_DIR` cache variable to point to the correct Python interpreter
(i.e. the virtual environment you have installed *pystencils-sfg* into).

(cmake_add_generator_scripts)=
### Add generator scripts

The primary interaction point in CMake is the function `pystencilssfg_generate_target_sources`,
with the following signature:

```CMake
pystencilssfg_generate_target_sources( <target> 
    SCRIPTS script1.py [script2.py ...]
    [DEPENDS dependency1.py [dependency2.py...]]
    [FILE_EXTENSIONS <header-extension> <impl-extension>]
    [OUTPUT_MODE <standalone|inline|header-only>]
    [CONFIG_MODULE <path-to-config-module.py>]
)
```

It registers the generator scripts `script1.py [script2.py ...]` to be executed at compile time using `add_custom_command`
and adds their output files to the specified `<target>`.
Any changes in the generator scripts, or any listed dependency, will trigger regeneration.
The function takes the following options:

 - `SCRIPTS`: A list of generator scripts
 - `DEPENDS`: A list of dependencies for the generator scripts
 - `FILE_EXTENSION`: The desired extensions for the generated files
 - `OUTPUT_MODE`: Sets the output mode of the code generator; see {any}`SfgConfig.output_mode`.
 - `CONFIG_MODULE`: Set the configuration module for all scripts registered with this call.
   If set, this overrides the value of `PystencilsSfg_CONFIG_MODULE`
   in the current scope (see [](#cmake_set_config_module))

### Include generated files

The `pystencils-sfg` CMake module creates a subfolder `sfg_sources/gen` at the root of the build tree
and writes all generated source files into it. The directory `sfg_sources` is added to the project's include
path, such that generated header files for a target `<target>` may be included via:
```C++
#include "gen/<target>/kernels.h"
```

(cmake_set_config_module)=
### Set a Configuration Module

There are two ways of specifying a [configuration module](#config_module) for generator scripts
registered with CMake:
- To set a configuration module for scripts registered with a single call to `pystencilssfg_generate_target_sources`,
  use the `CONFIG_MODULE` function parameter (see [](#cmake_add_generator_scripts)).
- To set a config module for all generator scripts within the current CMake directory and its subdirectories,
  set the scoped variable `PystencilsSfg_CONFIG_MODULE` to point at the respective Python file, e.g.
  `set( PystencilsSfg_CONFIG_MODULE ProjectConfig.py )`.

You might want to populate your configuration module with information about the current
build setup and environment.
For this purpose, take a look at the
[configure_file](https://cmake.org/cmake/help/latest/command/configure_file.html) CMake function.
