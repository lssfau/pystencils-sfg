# TODO
# mypy strict_optional=False

import sys
import os
from os import path

from .configuration import (
    SfgConfiguration,
    config_from_commandline,
    merge_configurations,
)
from .context import SfgContext


class SourceFileGenerator:
    """Context manager that controls the code generation process in generator scripts.

    ## Configuration

    The [source file generator][pystencilssfg.SourceFileGenerator] draws configuration from a total of four sources:

     - The [default configuration][pystencilssfg.configuration.DEFAULT_CONFIG];
     - The project configuration;
     - Command-line arguments;
     - The user configuration passed to the constructor of `SourceFileGenerator`.

    They take precedence in the following way:

     - Project configuration overrides the default configuration
     - Command line arguments override the project configuration
     - User configuration overrides default and project configuration,
       and must not conflict with command-line arguments; otherwise, an error is thrown.

    ### Project Configuration via Configurator Script

    Currently, the only way to define the project configuration is via a configuration module.
    A configurator module is a Python file defining the following function at the top-level:

    ```Python
    from pystencilssfg import SfgConfiguration

    def sfg_config() -> SfgConfiguration:
        # ...
        return SfgConfiguration(
            # ...
        )
    ```

    The configuration module is passed to the code generation script via the command-line argument
    `--sfg-config-module`.
    """

    def __init__(self, sfg_config: SfgConfiguration | None = None):
        if sfg_config and not isinstance(sfg_config, SfgConfiguration):
            raise TypeError("sfg_config is not an SfgConfiguration.")

        import __main__

        scriptpath = __main__.__file__
        scriptname = path.split(scriptpath)[1]
        basename = path.splitext(scriptname)[0]

        project_config, cmdline_config, script_args = config_from_commandline(sys.argv)

        config = merge_configurations(project_config, cmdline_config, sfg_config)

        self._context = SfgContext(
            config.outer_namespace, config.codestyle, argv=script_args
        )

        from .emission import HeaderImplPairEmitter

        self._emitter = HeaderImplPairEmitter(config.get_output_spec(basename))

    def clean_files(self):
        for file in self._emitter.output_files:
            if path.exists(file):
                os.remove(file)

    def __enter__(self) -> SfgContext:
        self.clean_files()
        return self._context

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._emitter.write_files(self._context)
