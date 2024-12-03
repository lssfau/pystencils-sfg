import os
from os import path

from .config import SfgConfig, CommandLineParameters, OutputMode, GLOBAL_NAMESPACE
from .context import SfgContext
from .composer import SfgComposer
from .emission import AbstractEmitter, OutputSpec
from .exceptions import SfgException


class SourceFileGenerator:
    """Context manager that controls the code generation process in generator scripts.

    The `SourceFileGenerator` must be used as a context manager by calling it within
    a ``with`` statement in the top-level code of a generator script (see :ref:`guide:generator_scripts`).
    Upon entry to its context, it creates an :class:`SfgComposer` which can be used to populate the generated files.
    When the managed region finishes, the code files are generated and written to disk at the locations
    defined by the configuration.
    Existing copies of the target files are deleted on entry to the managed region,
    and if an exception occurs within the managed region, no files are exported.

    Args:
        sfg_config: Inline configuration for the code generator
        keep_unknown_argv: If `True`, any command line arguments given to the generator script
            that the `SourceFileGenerator` does not understand are stored in
            `sfg.context.argv`.
    """

    def __init__(
        self, sfg_config: SfgConfig | None = None, keep_unknown_argv: bool = False
    ):
        if sfg_config and not isinstance(sfg_config, SfgConfig):
            raise TypeError("sfg_config is not an SfgConfiguration.")

        import __main__

        if not hasattr(__main__, "__file__"):
            raise SfgException(
                "Invalid execution environment: "
                "It seems that you are trying to run the `SourceFileGenerator` in an environment "
                "without a valid entry point, such as a REPL or a multiprocessing fork."
            )

        scriptpath = __main__.__file__
        scriptname = path.split(scriptpath)[1]
        basename = path.splitext(scriptname)[0]

        from argparse import ArgumentParser

        parser = ArgumentParser(
            scriptname,
            description="Generator script using pystencils-sfg",
            allow_abbrev=False,
        )
        CommandLineParameters.add_args_to_parser(parser)

        if keep_unknown_argv:
            sfg_args, script_args = parser.parse_known_args()
        else:
            sfg_args = parser.parse_args()
            script_args = []

        cli_params = CommandLineParameters(sfg_args)

        config = cli_params.get_config()
        if sfg_config is not None:
            cli_params.find_conflicts(sfg_config)
            config.override(sfg_config)

        self._context = SfgContext(
            None if config.outer_namespace is GLOBAL_NAMESPACE else config.outer_namespace,  # type: ignore
            config.codestyle,
            argv=script_args,
            project_info=cli_params.get_project_info(),
        )

        from pystencilssfg.ir import SfgHeaderInclude

        self._context.add_include(SfgHeaderInclude("cstdint", system_header=True))
        self._context.add_definition("#define RESTRICT __restrict__")

        output_mode = config.get_option("output_mode")
        output_spec = OutputSpec.create(config, basename)

        self._emitter: AbstractEmitter
        match output_mode:
            case OutputMode.HEADER_ONLY:
                from .emission import HeaderOnlyEmitter

                self._emitter = HeaderOnlyEmitter(
                    output_spec, clang_format=config.clang_format
                )
            case OutputMode.INLINE:
                from .emission import HeaderImplPairEmitter

                self._emitter = HeaderImplPairEmitter(
                    output_spec, inline_impl=True, clang_format=config.clang_format
                )
            case OutputMode.STANDALONE:
                from .emission import HeaderImplPairEmitter

                self._emitter = HeaderImplPairEmitter(
                    output_spec, clang_format=config.clang_format
                )

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
