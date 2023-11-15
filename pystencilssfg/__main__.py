import sys
from os import path

from argparse import ArgumentParser

from .configuration import (
    SfgConfigException, SfgConfigSource,
    add_config_args_to_parser, config_from_parser_args, merge_configurations
)


def main():
    parser = ArgumentParser("pystencilssfg",
                            description="pystencilssfg command-line utility")

    subparsers = parser.add_subparsers(required=True, title="Subcommands")

    version_parser = subparsers.add_parser(
        "version", help="Print version and exit.")
    version_parser.set_defaults(func=version)

    outfiles_parser = subparsers.add_parser(
        "list-files", help="List files produced by given codegen script.")

    outfiles_parser.set_defaults(func=list_files)
    outfiles_parser.add_argument(
        "--format", type=str, choices=("human", "cmake"), default="human")
    outfiles_parser.add_argument("codegen_script", type=str)

    add_config_args_to_parser(outfiles_parser)

    args = parser.parse_args()
    args.func(args)


def version(args, argv):
    from . import __version__
    print(__version__)
    exit(0)


def list_files(args):
    try:
        project_config, cmdline_config = config_from_parser_args(args)
    except SfgConfigException as exc:
        abort_with_config_exception(exc)

    config = merge_configurations(project_config, cmdline_config, None)

    scriptdir, scriptname = path.split(args.codegen_script)
    basename = path.splitext(scriptname)[0]

    from .emitters.cpu.basic_cpu import BasicCpuEmitter

    emitter = BasicCpuEmitter(basename, config)

    match args.format:
        case "human": print(" ".join(emitter.output_files))
        case "cmake": print(";".join(emitter.output_files), end="")

    exit(0)


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


main()
