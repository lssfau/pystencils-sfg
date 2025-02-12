from pystencilssfg import SourceFileGenerator, SfgConfig

#   Do not use clang-format, since it reorders headers
cfg = SfgConfig()
cfg.clang_format.skip = True

with SourceFileGenerator(cfg) as sfg:
    sfg.namespace("awesome")

    sfg.prelude("Expect the unexpected, and you shall never be surprised.")
    sfg.include("<iostream>")
    sfg.include("config.h")

    sfg.code("#define PI 3.1415")
    sfg.code("using namespace std;")
