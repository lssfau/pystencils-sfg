from pystencilssfg import SourceFileGenerator
from argparse import ArgumentParser

parser = ArgumentParser()
# set up parser ...

with SourceFileGenerator(keep_unknown_argv=True) as sfg:
    args = parser.parse_args(sfg.context.argv)
    ...
