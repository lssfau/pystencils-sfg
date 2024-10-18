from pystencilssfg import SourceFileGenerator, SfgConfiguration, SfgCodeStyle

#   Do not use clang-format, since it reorders headers
cfg = SfgConfiguration(
    codestyle=SfgCodeStyle(skip_clang_format=True)
)

with SourceFileGenerator(cfg) as sfg:
    sfg.prelude("Expect the unexpected, and you shall never be surprised.")
    sfg.include("<iostream>")
    sfg.include("config.h")

    sfg.namespace("awesome")

    sfg.code("#define PI 3.1415")
    sfg.code("using namespace std;")
