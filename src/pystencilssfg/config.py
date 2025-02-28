from __future__ import annotations

from argparse import ArgumentParser, BooleanOptionalAction

from types import ModuleType
from typing import Any, Sequence, Callable
from dataclasses import dataclass
from os import path
from importlib import util as iutil
from pathlib import Path

from pystencils.codegen.config import ConfigBase, Option, BasicOption, Category

from .lang import HeaderFile


class SfgConfigException(Exception): ...  # noqa: E701


@dataclass
class FileExtensions(ConfigBase):
    """BasicOption category containing output file extensions."""

    header: BasicOption[str] = BasicOption("hpp")
    """File extension for generated header file."""

    impl: BasicOption[str] = BasicOption("cpp")
    """File extension for generated implementation file."""

    @header.validate
    @impl.validate
    def _validate_extension(self, ext: str | None) -> str | None:
        if ext is not None and ext[0] == ".":
            return ext[1:]

        return ext


@dataclass
class CodeStyle(ConfigBase):
    """Options affecting the code style used by the source file generator."""

    indent_width: BasicOption[int] = BasicOption(2)
    """The number of spaces successively nested blocks should be indented with"""

    includes_sorting_key: BasicOption[Callable[[HeaderFile], Any]] = BasicOption()
    """Key function that will be used to sort ``#include`` statements in generated files.

    Pystencils-sfg will instruct clang-tidy to forego include sorting if this option is set.
    """

    #   TODO possible future options:
    #    - newline before opening {
    #    - trailing return types

    def indent(self, s: str):
        from textwrap import indent

        prefix = " " * self.get_option("indent_width")
        return indent(s, prefix)


@dataclass
class ClangFormatOptions(ConfigBase):
    """Options affecting the invocation of ``clang-format`` for automatic code formatting."""

    code_style: BasicOption[str] = BasicOption("file")
    """Code style to be used by clang-format. Passed verbatim to ``--style`` argument of the clang-format CLI.

    Similar to clang-format itself, the default value is ``file``, such that a ``.clang-format`` file found in the build
    tree will automatically be used.
    """

    force: BasicOption[bool] = BasicOption(False)
    """If set to ``True``, abort code generation if ``clang-format`` binary cannot be found."""

    skip: BasicOption[bool] = BasicOption(False)
    """If set to ``True``, skip formatting using ``clang-format``."""

    binary: BasicOption[str] = BasicOption("clang-format")
    """Path to the clang-format executable"""

    @force.validate
    def _validate_force(self, val: bool) -> bool:
        if val and self.skip:
            raise SfgConfigException(
                "Cannot set both `clang_format.force` and `clang_format.skip` at the same time"
            )
        return val

    @skip.validate
    def _validate_skip(self, val: bool) -> bool:
        if val and self.force:
            raise SfgConfigException(
                "Cannot set both `clang_format.force` and `clang_format.skip` at the same time"
            )
        return val


class _GlobalNamespace: ...  # noqa: E701


GLOBAL_NAMESPACE = _GlobalNamespace()
"""Indicates the C++ global namespace."""


@dataclass
class SfgConfig(ConfigBase):
    """Configuration options for the `SourceFileGenerator`."""

    extensions: Category[FileExtensions] = Category(FileExtensions())
    """File extensions of the generated files

    Options in this category:
        .. autosummary::
            FileExtensions.header
            FileExtensions.impl
    """

    header_only: BasicOption[bool] = BasicOption(False)
    """If set to `True`, generate only a header file.

    This will cause all definitions to be generated ``inline``.
    """

    outer_namespace: BasicOption[str | _GlobalNamespace] = BasicOption(GLOBAL_NAMESPACE)
    """The outermost namespace in the generated file. May be a valid C++ nested namespace qualifier
    (like ``a::b::c``) or `GLOBAL_NAMESPACE` if no outer namespace should be generated.

    .. autosummary::
        GLOBAL_NAMESPACE
    """

    codestyle: Category[CodeStyle] = Category(CodeStyle())
    """Options affecting the code style emitted by pystencils-sfg.

    Options in this category:
        .. autosummary::
            CodeStyle.indent_width
    """

    clang_format: Category[ClangFormatOptions] = Category(ClangFormatOptions())
    """Options governing the code style used by the code generator

    Options in this category:
        .. autosummary::
            ClangFormatOptions.code_style
            ClangFormatOptions.force
            ClangFormatOptions.skip
            ClangFormatOptions.binary
    """

    output_directory: Option[Path, str | Path] = Option(Path("."))
    """Directory to which the generated files should be written."""

    @output_directory.validate
    def _validate_output_directory(self, pth: str | Path) -> Path:
        return Path(pth)

    def _get_output_files(self, basename: str):
        output_dir: Path = self.get_option("output_directory")

        header_ext = self.extensions.get_option("header")
        impl_ext = self.extensions.get_option("impl")
        output_files = [output_dir / f"{basename}.{header_ext}"]
        header_only = self.get_option("header_only")

        if not header_only:
            assert impl_ext is not None
            output_files.append(output_dir / f"{basename}.{impl_ext}")

        return tuple(output_files)


class CommandLineParameters:
    @staticmethod
    def add_args_to_parser(parser: ArgumentParser):
        config_group = parser.add_argument_group("Configuration")

        config_group.add_argument(
            "--sfg-output-dir", type=str, default=None, dest="output_directory"
        )
        config_group.add_argument(
            "--sfg-file-extensions",
            type=str,
            default=None,
            dest="file_extensions",
            help="Comma-separated list of file extensions",
        )
        config_group.add_argument(
            "--sfg-header-only",
            action=BooleanOptionalAction,
            dest="header_only",
            help="Generate only a header file.",
        )
        config_group.add_argument(
            "--sfg-config-module", type=str, default=None, dest="config_module_path"
        )

        return parser

    def __init__(self, args) -> None:
        self._cl_config_module_path: str | None = args.config_module_path

        self._cl_header_only: bool | None = args.header_only
        self._cl_output_dir: str | None = args.output_directory

        if args.file_extensions is not None:
            file_extentions = list(args.file_extensions.split(","))
            h_ext, impl_ext = self._get_file_extensions(file_extentions)
            self._cl_header_ext = h_ext
            self._cl_impl_ext = impl_ext
        else:
            self._cl_header_ext = None
            self._cl_impl_ext = None

        self._config_module: ModuleType | None
        if self._cl_config_module_path is not None:
            self._config_module = self._import_config_module(
                self._cl_config_module_path
            )
        else:
            self._config_module = None

    @property
    def configuration_module(self) -> ModuleType | None:
        return self._config_module

    def get_config(self) -> SfgConfig:
        cfg = SfgConfig()
        if self._config_module is not None and hasattr(
            self._config_module, "configure_sfg"
        ):
            self._config_module.configure_sfg(cfg)

        if self._cl_header_only is not None:
            cfg.header_only = self._cl_header_only
        if self._cl_header_ext is not None:
            cfg.extensions.header = self._cl_header_ext
        if self._cl_impl_ext is not None:
            cfg.extensions.impl = self._cl_impl_ext
        if self._cl_output_dir is not None:
            cfg.output_directory = self._cl_output_dir

        return cfg

    def find_conflicts(self, cfg: SfgConfig):
        for name, mine, theirs in (
            ("header_only", self._cl_header_only, cfg.header_only),
            ("extensions.header", self._cl_header_ext, cfg.extensions.header),
            ("extensions.impl", self._cl_impl_ext, cfg.extensions.impl),
            ("output_directory", self._cl_output_dir, cfg.output_directory),
        ):
            if mine is not None and theirs is not None and mine != theirs:
                raise SfgConfigException(
                    f"Conflicting values given for option {name} on command line and inside generator script.\n"
                    f"    Value on command-line: {name}",
                    f"    Value in script: {name}",
                )

    def get_project_info(self) -> Any:
        if self._config_module is not None and hasattr(
            self._config_module, "project_info"
        ):
            return self._config_module.project_info()
        else:
            return None

    def _get_file_extensions(self, extensions: Sequence[str]):
        h_ext = None
        src_ext = None

        extensions = tuple(ext.strip() for ext in extensions)
        extensions = tuple((ext[1:] if ext[0] == "." else ext) for ext in extensions)

        HEADER_FILE_EXTENSIONS = {"h", "hpp", "hxx", "h++", "cuh"}
        IMPL_FILE_EXTENSIONS = {"c", "cpp", "cxx", "c++", "cu", "hip"}

        for ext in extensions:
            if ext in HEADER_FILE_EXTENSIONS:
                if h_ext is not None:
                    raise SfgConfigException(
                        "Multiple header file extensions specified."
                    )
                h_ext = ext
            elif ext in IMPL_FILE_EXTENSIONS:
                if src_ext is not None:
                    raise SfgConfigException(
                        "Multiple source file extensions specified."
                    )
                src_ext = ext
            else:
                raise SfgConfigException(
                    f"Invalid file extension: Don't know what to do with '.{ext}'"
                )

        return h_ext, src_ext

    def _import_config_module(self, module_path: str) -> ModuleType:
        cfg_modulename = path.splitext(path.split(module_path)[1])[0]

        cfg_spec = iutil.spec_from_file_location(cfg_modulename, module_path)

        if cfg_spec is None:
            raise SfgConfigException(
                f"Unable to import configuration module {module_path}",
            )

        config_module = iutil.module_from_spec(cfg_spec)
        cfg_spec.loader.exec_module(config_module)  # type: ignore
        return config_module
