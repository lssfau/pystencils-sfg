from pathlib import Path

from typing import Callable, Any
from .config import (
    SfgConfig,
    CommandLineParameters,
    _GlobalNamespace,
)
from .context import SfgContext
from .composer import SfgComposer
from .emission import SfgCodeEmitter
from .exceptions import SfgException
from .lang import HeaderFile


class SourceFileGenerator:
    """Context manager that controls the code generation process in generator scripts.

    The `SourceFileGenerator` must be used as a context manager by calling it within
    a ``with`` statement in the top-level code of a generator script.
    Upon entry to its context, it creates an `SfgComposer` which can be used to populate the generated files.
    When the managed region finishes, the code files are generated and written to disk at the locations
    defined by the configuration.
    Existing copies of the target files are deleted on entry to the managed region,
    and if an exception occurs within the managed region, no files are exported.

    Args:
        sfg_config: Inline configuration for the code generator
        keep_unknown_argv: If `True`, any command line arguments given to the generator script
            that the `SourceFileGenerator` does not understand are stored in
            `sfg.context.argv <SfgContext.argv>`.
    """

    def _scriptname(self) -> str:
        import __main__

        if not hasattr(__main__, "__file__"):
            raise SfgException(
                "Invalid execution environment: "
                "It seems that you are trying to run the `SourceFileGenerator` in an environment "
                "without a valid entry point, such as a REPL or a multiprocessing fork."
            )

        scriptpath = Path(__main__.__file__)
        return scriptpath.name

    def __init__(
        self,
        sfg_config: SfgConfig | None = None,
        keep_unknown_argv: bool = False,
    ):
        if sfg_config and not isinstance(sfg_config, SfgConfig):
            raise TypeError("sfg_config is not an SfgConfiguration.")

        scriptname = self._scriptname()
        basename = scriptname.rsplit(".")[0]

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

        self._header_only: bool = config.get_option("header_only")
        self._output_dir: Path = config.get_option("output_directory")

        output_files = config._get_output_files(basename)

        from .ir import SfgSourceFile, SfgSourceFileType

        self._header_file = SfgSourceFile(
            output_files[0].name, SfgSourceFileType.HEADER
        )
        self._impl_file: SfgSourceFile | None

        if self._header_only:
            self._impl_file = None
        else:
            self._impl_file = SfgSourceFile(
                output_files[1].name, SfgSourceFileType.TRANSLATION_UNIT
            )
            self._impl_file.includes.append(HeaderFile.parse(self._header_file.name))

        #   TODO: Find a way to not hard-code the restrict qualifier in pystencils
        self._header_file.elements.append("#define RESTRICT __restrict__")

        outer_namespace: str | _GlobalNamespace = config.get_option("outer_namespace")

        namespace: str | None
        if isinstance(outer_namespace, _GlobalNamespace):
            namespace = None
        else:
            namespace = outer_namespace

        self._context = SfgContext(
            self._header_file,
            self._impl_file,
            namespace,
            config.codestyle,
            config.clang_format,
            argv=script_args,
            project_info=cli_params.get_project_info(),
        )

        sort_key = config.codestyle.get_option("includes_sorting_key")
        if sort_key is None:

            def default_key(h: HeaderFile):
                return str(h)

            sort_key = default_key

        self._include_sort_key: Callable[[HeaderFile], Any] = sort_key

    def clean_files(self):
        header_path = self._output_dir / self._header_file.name
        if header_path.exists():
            header_path.unlink()

        if self._impl_file is not None:
            impl_path = self._output_dir / self._impl_file.name
            if impl_path.exists():
                impl_path.unlink()

    def _finish_files(self) -> None:
        from .ir import collect_includes

        header_includes = collect_includes(self._header_file)
        self._header_file.includes = list(
            set(self._header_file.includes) | header_includes
        )
        self._header_file.includes.sort(key=self._include_sort_key)

        if self._impl_file is not None:
            impl_includes = collect_includes(self._impl_file)
            #   If some header is already included by the generated header file, do not duplicate that inclusion
            impl_includes -= header_includes
            self._impl_file.includes = list(
                set(self._impl_file.includes) | impl_includes
            )
            self._impl_file.includes.sort(key=self._include_sort_key)

    def _get_emitter(self):
        return SfgCodeEmitter(
            self._output_dir,
            self._context.codestyle,
            self._context.clang_format,
        )

    def __enter__(self) -> SfgComposer:
        self.clean_files()
        return SfgComposer(self._context)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._finish_files()

            emitter = self._get_emitter()
            emitter.emit(self._header_file)
            if self._impl_file is not None:
                emitter.emit(self._impl_file)
