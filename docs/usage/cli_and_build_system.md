
## Command Line Interface

*pystencils-sfg* exposes not one, but two command line interfaces:
The *global CLI* offers a few tools meant to be used by build systems,
while the *generator script* command line interface is meant for a build system to communicate
with the code generator during on-the-fly generation.

### Global CLI

The global CLI may be accessed either through the `sfg-cli` shell command, or using `python -m pystencilssfg`.

### Generator Script CLI

The [SourceFileGenerator][pystencilssfg.SourceFileGenerator] evaluates a generator script's command line arguments,
which can be supplied by the user, but more frequently by the build system.

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

### Add generator scripts

The primary interaction point in CMake is the function `pystencilssfg_generate_target_sources`,
with the following signature:

```CMake
pystencilssfg_generate_target_sources( <target> 
    SCRIPTS script1.py [script2.py ...]
    [DEPENDS dependency1.py [dependency2.py...]]
    [FILE_EXTENSIONS <header-extension> <impl-extension>]
    [HEADER_ONLY])
```

It registers the generator scripts `script1.py [script2.py ...]` to be executed at compile time using `add_custom_command`
and adds their output files to the specified `<target>`.
Any changes in the generator scripts, or any listed dependency, will trigger regeneration.
The function takes the following options:

 - `SCRIPTS`: A list of generator scripts
 - `DEPENDS`: A list of dependencies for the generator scripts
 - `FILE_EXTENSION`: The desired extensions for the generated files
 - `HEADER_ONLY`: Toggles header-only code generation

### Include generated files

The `pystencils-sfg` CMake module creates a subfolder `sfg_sources/gen` at the root of the build tree
and writes all generated source files into it. The directory `sfg_sources` is added to the project's include
path, such that generated header files for a target `<target>` may be included via:
```C++
#include "gen/<target>/kernels.h"
```

### Project Configuration

The *pystencils-sfg* CMake module reads the scoped variable `PystencilsSfg_CONFIGURATOR_SCRIPT` to find
the *configuration module* that should be passed to the generator scripts.
