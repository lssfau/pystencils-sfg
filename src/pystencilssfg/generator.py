# TODO
# mypy strict_optional=False

import sys
import os
from os import path

from .configuration import (
    SfgConfiguration,
    SfgOutputMode,
    config_from_commandline,
    merge_configurations,
)
from .context import SfgContext
from .composer import SfgComposer
from .emission import AbstractEmitter


class SourceFileGenerator:
    """Context manager that controls the code generation process in generator scripts.

    **Usage:** The `SourceFileGenerator` must be used as a context manager by calling it within
    a ``with`` statement in the top-level code of a generator script (see :ref:`guide:generator_scripts`).
    Upon entry to its context, it creates an :class:`SfgComposer` which can be used to populate the generated files.
    When the managed region finishes, the code files are generated and written to disk at the locations
    defined by the configuration.
    Existing copies of the target files are deleted on entry to the managed region,
    and if an exception occurs within the managed region, no files are exported.

    **Configuration:** The `SourceFileGenerator` optionally takes a user-defined configuration
    object which is merged with configuration obtained from the build system; for details
    on configuration sources, refer to :class:`SfgConfiguration`.

    Args:
        sfg_config: User configuration for the code generator
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

        assert config.codestyle is not None

        self._context = SfgContext(
            config.outer_namespace,
            config.codestyle,
            argv=script_args,
            project_info=config.project_info,
        )

        self._emitter: AbstractEmitter
        match config.output_mode:
            case SfgOutputMode.HEADER_ONLY:
                from .emission import HeaderOnlyEmitter

                self._emitter = HeaderOnlyEmitter(config.get_output_spec(basename))
            case SfgOutputMode.INLINE:
                from .emission import HeaderImplPairEmitter

                self._emitter = HeaderImplPairEmitter(
                    config.get_output_spec(basename), inline_impl=True
                )
            case SfgOutputMode.STANDALONE:
                from .emission import HeaderImplPairEmitter

                self._emitter = HeaderImplPairEmitter(config.get_output_spec(basename))

    def clean_files(self):
        for file in self._emitter.output_files:
            if path.exists(file):
                os.remove(file)

    def __enter__(self) -> SfgComposer:
        self.clean_files()
        return SfgComposer(self._context)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._emitter.write_files(self._context)
