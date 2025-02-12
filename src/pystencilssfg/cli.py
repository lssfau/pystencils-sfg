import sys
import os
from os import path
from typing import NoReturn

from argparse import ArgumentParser, BooleanOptionalAction

from .config import CommandLineParameters, SfgConfigException


def add_newline_arg(parser):
    parser.add_argument(
        "--newline",
        action=BooleanOptionalAction,
        default=True,
        help="Whether to add a terminating newline to the output.",
    )


def cli_main(program="sfg-cli") -> NoReturn:
    parser = ArgumentParser(
        program,
        description="pystencilssfg command-line utility for build system integration",
    )

    subparsers = parser.add_subparsers(required=True, title="Subcommands")

    version_parser = subparsers.add_parser("version", help="Print version and exit.")
    add_newline_arg(version_parser)
    version_parser.set_defaults(func=version)

    outfiles_parser = subparsers.add_parser(
        "list-files", help="List files produced by given codegen script."
    )

    outfiles_parser.set_defaults(func=list_files)
    CommandLineParameters.add_args_to_parser(outfiles_parser)
    add_newline_arg(outfiles_parser)
    outfiles_parser.add_argument(
        "--sep", type=str, default=" ", dest="sep", help="Separator for list items"
    )
    outfiles_parser.add_argument("codegen_script", type=str)

    cmake_parser = subparsers.add_parser(
        "cmake", help="Operations for CMake integation"
    )
    cmake_subparsers = cmake_parser.add_subparsers(required=True)

    modpath = cmake_subparsers.add_parser(
        "modulepath", help="Print the include path for the pystencils-sfg cmake module"
    )
    add_newline_arg(modpath)
    modpath.set_defaults(func=print_cmake_modulepath)

    findmod = cmake_subparsers.add_parser(
        "make-find-module",
        help="Creates the pystencils-sfg CMake find module as"
        + "'FindPystencilsSfg.cmake' in the current directory.",
    )
    findmod.set_defaults(func=make_cmake_find_module)

    args = parser.parse_args()
    args.func(args)

    exit(-1)  # should never happen


def version(args) -> NoReturn:
    from . import __version__

    print(__version__, end=os.linesep if args.newline else "")

    exit(0)


def list_files(args) -> NoReturn:
    cli_params = CommandLineParameters(args)
    config = cli_params.get_config()

    _, scriptname = path.split(args.codegen_script)
    basename = path.splitext(scriptname)[0]

    output_files = config._get_output_files(basename)

    print(
        args.sep.join(str(of) for of in output_files),
        end=os.linesep if args.newline else "",
    )

    exit(0)


def print_cmake_modulepath(args) -> NoReturn:
    from .cmake import get_sfg_cmake_modulepath

    print(get_sfg_cmake_modulepath(), end=os.linesep if args.newline else "")
    exit(0)


def make_cmake_find_module(args) -> NoReturn:
    from .cmake import make_find_module

    make_find_module()
    exit(0)


def abort_with_config_exception(exception: SfgConfigException, source: str) -> NoReturn:
    print(f"Invalid {source} configuration: {exception.args[0]}.", file=sys.stderr)
    exit(1)
