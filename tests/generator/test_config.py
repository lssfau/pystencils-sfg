import pytest

from pystencilssfg.config import (
    SfgConfig,
    OutputMode,
    GLOBAL_NAMESPACE,
    CommandLineParameters,
    SfgConfigException
)


def test_defaults():
    cfg = SfgConfig()

    assert cfg.get_option("output_mode") == OutputMode.STANDALONE
    assert cfg.extensions.get_option("header") == "hpp"
    assert cfg.codestyle.get_option("indent_width") == 2
    assert cfg.clang_format.get_option("binary") == "clang-format"
    assert cfg.clang_format.get_option("code_style") == "file"
    assert cfg.get_option("outer_namespace") is GLOBAL_NAMESPACE

    cfg.extensions.impl = ".cu"
    assert cfg.extensions.get_option("impl") == "cu"

    #   Check that section subobjects of different config objects are independent
    #   -> must use default_factory to construct them, because they are mutable!
    cfg.clang_format.binary = "bogus"

    cfg2 = SfgConfig()
    assert cfg2.clang_format.binary is None


def test_override():
    cfg1 = SfgConfig()
    cfg1.outer_namespace = "test"
    cfg1.extensions.header = "h"
    cfg1.extensions.impl = "c"
    cfg1.clang_format.force = True

    cfg2 = SfgConfig()
    cfg2.outer_namespace = GLOBAL_NAMESPACE
    cfg2.extensions.header = "hpp"
    cfg2.extensions.impl = "cpp"
    cfg2.clang_format.binary = "bogus"

    cfg1.override(cfg2)

    assert cfg1.outer_namespace is GLOBAL_NAMESPACE
    assert cfg1.extensions.header == "hpp"
    assert cfg1.extensions.impl == "cpp"
    assert cfg1.codestyle.indent_width is None
    assert cfg1.clang_format.force is True
    assert cfg1.clang_format.code_style is None
    assert cfg1.clang_format.binary == "bogus"


def test_sanitation():
    cfg = SfgConfig()

    cfg.extensions.header = ".hxx"
    assert cfg.extensions.header == "hxx"

    cfg.extensions.header = ".cxx"
    assert cfg.extensions.header == "cxx"

    cfg.clang_format.force = True
    with pytest.raises(SfgConfigException):
        cfg.clang_format.skip = True

    cfg.clang_format.force = False
    cfg.clang_format.skip = True
    with pytest.raises(SfgConfigException):
        cfg.clang_format.force = True


def test_from_commandline(sample_config_module):
    from argparse import ArgumentParser

    parser = ArgumentParser()
    CommandLineParameters.add_args_to_parser(parser)

    args = parser.parse_args(
        ["--sfg-output-dir", ".out", "--sfg-file-extensions", ".h++,c++"]
    )

    cli_args = CommandLineParameters(args)
    cfg = cli_args.get_config()

    assert cfg.output_directory == ".out"
    assert cfg.extensions.header == "h++"
    assert cfg.extensions.impl == "c++"

    args = parser.parse_args(
        ["--sfg-output-dir", "gen_sources", "--sfg-config-module", sample_config_module]
    )
    cli_args = CommandLineParameters(args)
    cfg = cli_args.get_config()

    assert cfg.codestyle.indent_width == 3
    assert cfg.clang_format.code_style == "llvm"
    assert cfg.clang_format.skip is True
    assert (
        cfg.output_directory == "gen_sources"
    )  # value from config module overridden by commandline
    assert cfg.outer_namespace == "myproject"
    assert cfg.extensions.header == "hpp"

    assert cli_args.configuration_module is not None
    assert cli_args.configuration_module.magic_string == "Spam and eggs"
    assert cli_args.configuration_module.magic_number == 0xCAFE
