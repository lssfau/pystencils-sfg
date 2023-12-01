"""
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
# mypy: strict_optional=False

from __future__ import annotations

from typing import Sequence, Any
from os import path
from enum import Enum, auto
from dataclasses import dataclass, replace, fields, InitVar
from argparse import ArgumentParser
from textwrap import indent

from importlib import util as iutil

from .exceptions import SfgException

HEADER_FILE_EXTENSIONS = {'h', 'hpp'}
IMPL_FILE_EXTENSIONS = {'c', 'cpp', '.impl.h'}


class SfgConfigSource(Enum):
    DEFAULT = auto()
    PROJECT = auto()
    COMMANDLINE = auto()
    SCRIPT = auto()


class SfgConfigException(Exception):
    def __init__(self, cfg_src: SfgConfigSource | None, message: str):
        super().__init__(cfg_src, message)
        self.message = message
        self.config_source = cfg_src


@dataclass
class SfgCodeStyle:
    indent_width: int = 2

    code_style: str = "LLVM"
    """Code style to be used by clang-format. Passed verbatim to `--style` argument of the clang-format CLI."""

    force_clang_format: bool = False
    """If set to True, abort code generation if `clang-format` binary cannot be found."""

    clang_format_binary: str = "clang-format"
    """Path to the clang-format executable"""

    def indent(self, s: str):
        prefix = " " * self.indent_width
        return indent(s, prefix)


@dataclass
class SfgOutputSpec:
    """Name and path specification for files output by the code generator.

    Filenames are constructed as `<output_directory>/<basename>.<extension>`."""

    output_directory: str
    """Directory to which the generated files should be written."""

    basename: str
    """Base name for output files."""

    header_extension: str
    """File extension for generated header file."""

    impl_extension: str
    """File extension for generated implementation file."""

    def get_header_filename(self):
        return f"{self.basename}.{self.header_extension}"

    def get_impl_filename(self):
        return f"{self.basename}.{self.impl_extension}"

    def get_header_filepath(self):
        return path.join(self.output_directory, self.get_header_filename())

    def get_impl_filepath(self):
        return path.join(self.output_directory, self.get_impl_filename())


@dataclass
class SfgConfiguration:
    config_source: InitVar[SfgConfigSource | None] = None

    header_extension: str | None = None
    """File extension for generated header file."""

    impl_extension: str | None = None
    """File extension for generated implementation file."""

    header_only: bool | None = None
    """If set to `True`, generate only a header file without accompaning source file."""

    outer_namespace: str | None = None
    """The outermost namespace in the generated file. May be a valid C++ nested namespace qualifier
    (like `a::b::c`) or `None` if no outer namespace should be generated."""

    codestyle: SfgCodeStyle | None = None
    """Code style that should be used by the code generator."""

    output_directory: str | None = None
    """Directory to which the generated files should be written."""

    project_info: Any = None
    """Object for managing project-specific information. To be set by the configurator script."""

    def __post_init__(self, cfg_src: SfgConfigSource | None = None):
        if self.header_only:
            raise SfgConfigException(cfg_src, "Header-only code generation is not implemented yet.")

        if self.header_extension and self.header_extension[0] == '.':
            self.header_extension = self.header_extension[1:]

        if self.impl_extension and self.impl_extension[0] == '.':
            self.impl_extension = self.impl_extension[1:]

    def override(self, other: SfgConfiguration):
        other_dict: dict[str, Any] = {k: v for k, v in _shallow_dict(other).items() if v is not None}
        return replace(self, **other_dict)

    def get_output_spec(self, basename: str) -> SfgOutputSpec:
        assert self.header_extension is not None
        assert self.impl_extension is not None
        assert self.output_directory is not None

        return SfgOutputSpec(
            self.output_directory,
            basename,
            self.header_extension,
            self.impl_extension
        )


DEFAULT_CONFIG = SfgConfiguration(
    config_source=SfgConfigSource.DEFAULT,
    header_extension='h',
    impl_extension='cpp',
    header_only=False,
    outer_namespace=None,
    codestyle=SfgCodeStyle(),
    output_directory="."
)


def run_configurator(configurator_script: str):
    cfg_modulename = path.splitext(path.split(configurator_script)[1])[0]

    cfg_spec = iutil.spec_from_file_location(cfg_modulename, configurator_script)

    if cfg_spec is None:
        raise SfgConfigException(SfgConfigSource.PROJECT,
                                 f"Unable to load configurator script {configurator_script}")

    configurator = iutil.module_from_spec(cfg_spec)
    cfg_spec.loader.exec_module(configurator)

    if not hasattr(configurator, "sfg_config"):
        raise SfgConfigException(SfgConfigSource.PROJECT, "Project configurator does not define function `sfg_config`.")

    project_config = configurator.sfg_config()
    if not isinstance(project_config, SfgConfiguration):
        raise SfgConfigException(SfgConfigSource.PROJECT, "sfg_config did not return a SfgConfiguration object.")

    return project_config


def add_config_args_to_parser(parser: ArgumentParser):
    config_group = parser.add_argument_group("Configuration")

    config_group.add_argument("--sfg-output-dir",
                              type=str, default=None, dest='output_directory')
    config_group.add_argument("--sfg-file-extensions",
                              type=str,
                              default=None,
                              dest='file_extensions',
                              help="Comma-separated list of file extensions")
    config_group.add_argument("--sfg-header-only", default=None, action='store_true', dest='header_only')
    config_group.add_argument("--sfg-config-module", type=str, default=None, dest='configurator_script')

    return parser


def config_from_parser_args(args):
    if args.configurator_script is not None:
        project_config = run_configurator(args.configurator_script)
    else:
        project_config = None

    if args.file_extensions is not None:
        file_extentions = list(args.file_extensions.split(","))
        h_ext, src_ext = _get_file_extensions(SfgConfigSource.COMMANDLINE, file_extentions)
    else:
        h_ext, src_ext = None, None

    cmdline_config = SfgConfiguration(
        config_source=SfgConfigSource.COMMANDLINE,
        header_extension=h_ext,
        impl_extension=src_ext,
        header_only=args.header_only,
        output_directory=args.output_directory
    )

    return project_config, cmdline_config


def config_from_commandline(argv: list[str]):
    parser = ArgumentParser("pystencilssfg",
                            description="pystencils Source File Generator",
                            allow_abbrev=False)

    add_config_args_to_parser(parser)

    args, script_args = parser.parse_known_args(argv)
    project_config, cmdline_config = config_from_parser_args(args)

    return project_config, cmdline_config, script_args


def merge_configurations(project_config: SfgConfiguration | None,
                         cmdline_config: SfgConfiguration | None,
                         script_config: SfgConfiguration | None):
    #   Project config completely overrides default config
    config = DEFAULT_CONFIG

    if project_config is not None:
        config = config.override(project_config)

    if cmdline_config is not None:
        cmdline_dict = _shallow_dict(cmdline_config)
        #   Commandline config completely overrides project and default config
        config = config.override(cmdline_config)
    else:
        cmdline_dict = {}

    if script_config is not None:
        #   User config may only set values not specified on the command line
        script_dict = _shallow_dict(script_config)
        for key, cmdline_value in cmdline_dict.items():
            if cmdline_value is not None and script_dict[key] is not None:
                raise SfgException(
                    "Conflicting configuration:"
                    + f" Parameter {key} was specified both in the script and on the command line.")

        config = config.override(script_config)

    return config


def _get_file_extensions(cfgsrc: SfgConfigSource, extensions: Sequence[str]):
    h_ext = None
    src_ext = None

    extensions = tuple((ext[1:] if ext[0] == '.' else ext) for ext in extensions)

    for ext in extensions:
        if ext in HEADER_FILE_EXTENSIONS:
            if h_ext is not None:
                raise SfgConfigException(cfgsrc, "Multiple header file extensions specified.")
            h_ext = ext
        elif ext in IMPL_FILE_EXTENSIONS:
            if src_ext is not None:
                raise SfgConfigException(cfgsrc, "Multiple source file extensions specified.")
            src_ext = ext
        else:
            raise SfgConfigException(cfgsrc, f"Don't know how to interpret file extension '.{ext}'")

    return h_ext, src_ext


def _shallow_dict(obj):
    """Workaround to create a shallow dict of a dataclass object, see
    https://docs.python.org/3/library/dataclasses.html#dataclasses.asdict."""
    return dict((field.name, getattr(obj, field.name)) for field in fields(obj))
