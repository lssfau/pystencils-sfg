
## Make CLion treat generated files as project sources

When working on a CMake project in [CLion](https://www.jetbrains.com/clion/) that uses `pystencils-sfg`'s CMake
module for on-the-fly code generation, it is likely that CLion refuses to treat generated files as project sources.
Instead, the IDE will show the message:

 > This file does not belong to any project target; code insight features might not work properly.

The reason behind this is that the generated files lie in the build directories.

To solve this, simply navigate to the CMake build directory in CLion's *Project* view,
right-click on the `sfg_sources` subfolder and select `Mark Directory as -> Project Sources and Headers`.
CLion should now treat all generated files in this directory as project source files.
