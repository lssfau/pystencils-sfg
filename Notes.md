
# Build System Integration

## Configurator Script

The configurator script should configure the code generator and provide global configuration to all codegen scripts.
In the CMake integration, it can be specified globally via the `PystencilsSfg_CONFIGURATOR_SCRIPT` cache variable.

To decide and implement:

 - Use `runpy` and communicate via a global variable, or use `importlib.util.spec_from_file_location` and communicate via
   a function call? In either case, there needs to be concensus about at least one name in the configurator script.
 - Allow specifying a separate configurator file at `pystencilssfg_generate_target_sources`? Sound sensible... It's basically
   for free with the potential to add lots of flexibility

## Generator flags

Two separate lists of flags may be passed to generator scripts: Some may be evaluated by the SFG, and the rest
will be passed on to the user script.

Arguments to the SFG include:

 - Path of the configurator script
 - Output directory

How to separate user from generator arguments? 

