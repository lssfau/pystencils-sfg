from pystencilssfg import SfgConfig


def configure_sfg(cfg: SfgConfig):
    cfg.outer_namespace = "myproject"
    cfg.codestyle.indent_width = 3


def project_info():
    return {
        "use_openmp": True,
        "use_cuda": True,
        "float_format": "float32",
    }
