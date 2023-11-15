from __future__ import annotations

from typing import List, Sequence, Any
from enum import Enum, auto
from dataclasses import dataclass, replace, asdict, InitVar
from argparse import ArgumentParser
from os import path

import importlib

from jinja2.filters import do_indent

from .exceptions import SfgException

HEADER_FILE_EXTENSIONS = {'h', 'hpp'}
SOURCE_FILE_EXTENSIONS = {'c', 'cpp'}


class SfgConfigSource(Enum):
    DEFAULT = auto()
    PROJECT = auto()
    COMMANDLINE = auto
    SCRIPT = auto()


class SfgConfigException(Exception):
    def __init__(self, cfg_src: SfgConfigSource, message: str):
        assert cfg_src != SfgConfigSource.DEFAULT, "Invalid default config. Contact a developer."

        super().__init__(cfg_src, message)
        self.message = message
        self.config_source = cfg_src


@dataclass
class SfgCodeStyle:
    indent_width: int = 2

    def indent(self, s: str):
        return do_indent(s, self.indent_width, first=True)


@dataclass
class SfgConfiguration:
    config_source: InitVar[SfgConfigSource | None] = None

    header_extension: str = None
    """File extension for generated header files."""

    source_extension: str = None
    """File extension for generated source files."""

    header_only: bool = None
    """If set to `True`, generate only a header file without accompaning source file."""

    base_namespace: str = None
    """The outermost namespace in the generated file. May be a valid C++ nested namespace qualifier
    (like `a::b::c`) or `None` if no outer namespace should be generated."""

    codestyle: SfgCodeStyle = None
    """Code style that should be used by the code generator."""

    output_directory: str = None
    """Directory to which the generated files should be written."""

    project_info: Any = None
    """Object for managing project-specific information. To be set by the configurator script."""

    def __post_init__(self, cfg_src: SfgConfigSource = None):
        if self.header_only:
            raise SfgConfigException(cfg_src, "Header-only code generation is not implemented yet.")

        if self.header_extension and self.header_extension[0] == '.':
            self.header_extension = self.header_extension[1:]

        if self.source_extension and self.source_extension[0] == '.':
            self.source_extension = self.source_extension[1:]

    def override(self, other: SfgConfiguration):
        other_dict = asdict(other)
        other_dict = {k: v for k, v in other_dict.items() if v is not None}
        return replace(self, **other_dict)


DEFAULT_CONFIG = SfgConfiguration(
    config_source=SfgConfigSource.DEFAULT,
    header_extension='h',
    source_extension='cpp',
    header_only=False,
    base_namespace=None,
    codestyle=SfgCodeStyle(),
    output_directory=""
)


def run_configurator(configurator_script: str):
    if not path.exists(configurator_script):
        raise SfgConfigException(SfgConfigSource.PROJECT,
                                 f"Configurator script not found: {configurator_script} is not a file.")

    cfg_spec = importlib.util.spec_from_file_location(configurator_script)
    configurator = importlib.util.module_from_spec(cfg_spec)

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
    config_group.add_argument("--sfg-configurator", type=str, default=None, dest='configurator_script')

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
        source_extension=src_ext,
        header_only=args.header_only,
        output_directory=args.output_directory
    )

    return project_config, cmdline_config


def config_from_commandline(argv: List[str]):
    parser = ArgumentParser("pystencilssfg",
                            description="pystencils Source File Generator",
                            allow_abbrev=False)

    add_config_args_to_parser(parser)

    args, script_args = parser.parse_known_args(argv)
    project_config, cmdline_config = config_from_parser_args(args)

    return project_config, cmdline_config, script_args


def merge_configurations(project_config: SfgConfiguration,
                         cmdline_config: SfgConfiguration,
                         script_config: SfgConfiguration):
    #   Project config completely overrides default config
    config = DEFAULT_CONFIG

    if project_config is not None:
        config = config.override(project_config)

    if cmdline_config is not None:
        cmdline_dict = asdict(cmdline_config)
        #   Commandline config completely overrides project and default config
        config = config.override(cmdline_config)
    else:
        cmdline_dict = {}

    if script_config is not None:
        #   User config may only set values not specified on the command line
        script_dict = asdict(script_config)
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

    extensions = ((ext[1:] if ext[0] == '.' else ext) for ext in extensions)

    for ext in extensions:
        if ext in HEADER_FILE_EXTENSIONS:
            if h_ext is not None:
                raise SfgConfigException(cfgsrc, "Multiple header file extensions specified.")
            h_ext = ext
        elif ext in SOURCE_FILE_EXTENSIONS:
            if src_ext is not None:
                raise SfgConfigException(cfgsrc, "Multiple source file extensions specified.")
            src_ext = ext
        else:
            raise SfgConfigException(cfgsrc, f"Don't know how to interpret file extension '.{ext}'")

    return h_ext, src_ext
