from pystencilssfg import SfgConfig


def configure(cfg: SfgConfig):
    cfg.extensions.header = "h++"
    cfg.extensions.impl = "c++"
