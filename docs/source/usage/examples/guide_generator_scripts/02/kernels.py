from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:
    sfg.include("<vector>")
    sfg.include("<span>")
    sfg.include("custom_header.hpp")
