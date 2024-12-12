from pystencilssfg import SourceFileGenerator

with SourceFileGenerator(keep_unknown_argv=True) as sfg:
    ctx = sfg.context

    assert ctx.argv == ["--precision", "float32", "test1", "test2"]
