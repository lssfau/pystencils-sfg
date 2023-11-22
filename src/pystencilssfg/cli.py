import sys
import os
from os import path

from argparse import ArgumentParser, BooleanOptionalAction

from .configuration import (
    SfgConfigException, SfgConfigSource,
    add_config_args_to_parser, config_from_parser_args, merge_configurations
)


def add_newline_arg(parser):
    parser.add_argument("--newline", action=BooleanOptionalAction, default=True,
                        help="Whether to add a terminating newline to the output.")


def cli_main(program='sfg-cli'):
    parser = ArgumentParser(program,
                            description="pystencilssfg command-line utility for build system integration")

    subparsers = parser.add_subparsers(required=True, title="Subcommands")

    version_parser = subparsers.add_parser("version", help="Print version and exit.")
    add_newline_arg(version_parser)
    version_parser.set_defaults(func=version)

    outfiles_parser = subparsers.add_parser(
        "list-files", help="List files produced by given codegen script.")

    outfiles_parser.set_defaults(func=list_files)
    add_config_args_to_parser(outfiles_parser)
    add_newline_arg(outfiles_parser)
    outfiles_parser.add_argument("--sep", type=str, default=" ", dest="sep", help="Separator for list items")
    outfiles_parser.add_argument("codegen_script", type=str)

    cmake_parser = subparsers.add_parser("cmake", help="Operations for CMake integation")
    cmake_subparsers = cmake_parser.add_subparsers(required=True)

    modpath = cmake_subparsers.add_parser(
        "modulepath", help="Print the include path for the pystencils-sfg cmake module")
    add_newline_arg(modpath)
    modpath.set_defaults(func=print_cmake_modulepath)

    findmod = cmake_subparsers.add_parser("make-find-module",
                                          help="Creates the pystencils-sfg CMake find module as" +
                                          "'FindPystencilsSfg.cmake' in the current directory.")
    findmod.set_defaults(func=make_cmake_find_module)

    args = parser.parse_args()
    args.func(args)

    exit(-1)  # should never happen


def version(args):
    from . import __version__

    print(__version__, end=os.linesep if args.newline else '')

    exit(0)


def list_files(args):
    try:
        project_config, cmdline_config = config_from_parser_args(args)
    except SfgConfigException as exc:
        abort_with_config_exception(exc)

    config = merge_configurations(project_config, cmdline_config, None)

    _, scriptname = path.split(args.codegen_script)
    basename = path.splitext(scriptname)[0]

    from .emitters.cpu.basic_cpu import BasicCpuEmitter

    emitter = BasicCpuEmitter(basename, config)

    print(args.sep.join(emitter.output_files), end=os.linesep if args.newline else '')

    exit(0)


def print_cmake_modulepath(args):
    from .cmake import get_sfg_cmake_modulepath
    print(get_sfg_cmake_modulepath(), end=os.linesep if args.newline else '')


def make_cmake_find_module(args):
    from .cmake import make_find_module
    make_find_module()


def abort_with_config_exception(exception: SfgConfigException):
    def eprint(*args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

    match exception.config_source:
        case SfgConfigSource.PROJECT:
            eprint(
                f"Invalid project configuration: {exception.message}\nCheck your configurator script.")
        case SfgConfigSource.COMMANDLINE:
            eprint(
                f"Invalid configuration on command line: {exception.message}")
        case _: assert False, "(Theoretically) unreachable code. Contact the developers."

    exit(1)
