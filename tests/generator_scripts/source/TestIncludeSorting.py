from pystencilssfg import SourceFileGenerator, SfgConfig
from pystencilssfg.lang import HeaderFile


def sortkey(h: HeaderFile):
    try:
        return [
            "memory",
            "vector",
            "array"
        ].index(h.filepath)
    except ValueError:
        return 100


cfg = SfgConfig()
cfg.codestyle.includes_sorting_key = sortkey


with SourceFileGenerator(cfg) as sfg:
    sfg.include("<array>")
    sfg.include("<memory>")
    sfg.include("<vector>")
