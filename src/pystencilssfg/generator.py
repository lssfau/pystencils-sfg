# TODO
# mypy strict_optional=False

import sys
import os
from os import path

from .configuration import SfgConfiguration, config_from_commandline, merge_configurations
from .context import SfgContext
from .composer import SfgComposer


class SourceFileGenerator:
    """Context manager that controls the code generation process in generator scripts."""
    def __init__(self, sfg_config: SfgConfiguration | None = None):
        if sfg_config and not isinstance(sfg_config, SfgConfiguration):
            raise TypeError("sfg_config is not an SfgConfiguration.")

        import __main__
        scriptpath = __main__.__file__
        scriptname = path.split(scriptpath)[1]
        basename = path.splitext(scriptname)[0]

        project_config, cmdline_config, script_args = config_from_commandline(sys.argv)

        config = merge_configurations(project_config, cmdline_config, sfg_config)

        self._context = SfgContext(config.outer_namespace, config.codestyle, argv=script_args)

        from .emission import HeaderSourcePairEmitter
        self._emitter = HeaderSourcePairEmitter(config.get_output_spec(basename))

    def clean_files(self):
        for file in self._emitter.output_files:
            if path.exists(file):
                os.remove(file)

    def __enter__(self):
        self.clean_files()
        return SfgComposer(self._context)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._emitter.write_files(self._context)
