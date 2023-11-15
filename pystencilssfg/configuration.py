from typing import List, Sequence
from enum import Enum, auto
from dataclasses import dataclass, replace
from argparse import ArgumentParser

from jinja2.filters import do_indent

from .exceptions import SfgException

HEADER_FILE_EXTENSIONS = {'h', 'hpp'}
SOURCE_FILE_EXTENSIONS = {'c', 'cpp'}


@dataclass
class SfgCodeStyle:
    indent_width: int = 2

    def indent(self, s: str):
        return do_indent(s, self.indent_width, first=True)


@dataclass
class SfgConfiguration:
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

    def __post_init__(self):
        if self.header_only:
            raise SfgException(
                "Header-only code generation is not implemented yet.")
        
        if self.header_extension[0] == '.':
            self.header_extension = self.header_extension[1:]

        if self.source_extension[0] == '.':
            self.source_extension = self.source_extension[1:]


DEFAULT_CONFIG = SfgConfiguration(
    header_extension='h',
    source_extension='cpp',
    header_only=False,
    base_namespace=None,
    codestyle=SfgCodeStyle(),
    output_directory=""
)


def get_file_extensions(self, extensions: Sequence[str]):
    h_ext = None
    src_ext = None

    extensions = ((ext[1:] if ext[0] == '.' else ext) for ext in extensions)

    for ext in extensions:
        if ext in HEADER_FILE_EXTENSIONS:
            if h_ext is not None:
                raise ValueError("Multiple header file extensions found.")
            h_ext = ext
        elif ext in SOURCE_FILE_EXTENSIONS:
            if src_ext is not None:
                raise ValueError("Multiple source file extensions found.")
            src_ext = ext
        else:
            raise ValueError(f"Don't know how to interpret extension '.{ext}'")

    return h_ext, src_ext


def run_configurator(configurator_script: str):
    raise NotImplementedError()


def config_from_commandline(self, argv: List[str]):
    parser = ArgumentParser("pystencilssfg",
                            description="pystencils Source File Generator",
                            allow_abbrev=False)

    parser.add_argument("-sfg-d", "--sfg-output-dir",
                        type=str, default='.', dest='output_directory')
    parser.add_argument("-sfg-e", "--sfg-file-extensions",
                        type=str, default=None, nargs='*', dest='file_extensions')
    parser.add_argument("--sfg-header-only",
                        type=str, default=None, nargs='*', dest='header_only')
    parser.add_argument("--sfg-configurator", type=str,
                        default=None, nargs='*', dest='configurator_script')

    args, script_args = parser.parse_known_args(argv)

    if args.configurator_script is not None:
        project_config = run_configurator(args.configurator_script)
    else:
        project_config = None

    if args.file_extensions is not None:
        h_ext, src_ext = get_file_extensions(args.file_extensions)
    else:
        h_ext, src_ext = None, None

    cmdline_config = SfgConfiguration(
        header_extension=h_ext,
        source_extension=src_ext,
        header_only=args.header_only,
        output_directory=args.output_directory
    )

    return project_config, cmdline_config, script_args


def merge_configurations(project_config: SfgConfiguration,
                         cmdline_config: SfgConfiguration,
                         script_config: SfgConfiguration):
    #   Project config completely overrides default config
    config = DEFAULT_CONFIG

    if project_config is not None:
        config = replace(DEFAULT_CONFIG, **(project_config.asdict()))

    if cmdline_config is not None:
        cmdline_dict = cmdline_config.asdict()
        #   Commandline config completely overrides project and default config
        config = replace(config, **cmdline_dict)
    else:
        cmdline_dict = {}

    if script_config is not None:
        #   User config may only set values not specified on the command line
        script_dict = script_config.asdict()
        for key, cmdline_value in cmdline_dict.items():
            if cmdline_value is not None and script_dict[key] is not None:
                raise SfgException(
                    f"Conflicting configuration: Parameter {key} was specified both in the script and on the command line.")

        config = replace(config, **script_dict)

    return config
