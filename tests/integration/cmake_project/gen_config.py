from pystencilssfg import SfgConfig


def configure_sfg(cfg: SfgConfig):
    cfg.extensions.impl = "c++"


def project_info():
    return 31
