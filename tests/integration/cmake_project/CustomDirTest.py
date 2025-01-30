from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:
    sfg.code("#define NOTHING")
