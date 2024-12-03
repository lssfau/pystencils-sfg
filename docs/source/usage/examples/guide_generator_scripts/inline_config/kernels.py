from pystencilssfg import SourceFileGenerator, SfgConfig

cfg = SfgConfig()
cfg.output_directory = "gen_src"
cfg.codestyle.indent_width = 4

with SourceFileGenerator(cfg) as sfg:
    ...
