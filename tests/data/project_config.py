from pystencilssfg import SfgConfig


def configure_sfg(cfg: SfgConfig):
    cfg.codestyle.indent_width = 3
    cfg.clang_format.code_style = "llvm"
    cfg.clang_format.skip = True
    cfg.output_directory = "generated_sources"
    cfg.outer_namespace = "myproject"
    cfg.extensions.header = "hpp"


magic_string = "Spam and eggs"
magic_number = 0xcafe


def project_info():
    return {
        "use_openmp": True,
        "use_cuda": True,
        "float_format": "float32"
    }
