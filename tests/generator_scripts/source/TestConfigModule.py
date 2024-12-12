from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:
    ctx = sfg.context

    assert ctx.outer_namespace == "myproject"
    assert ctx.codestyle.indent_width == 3

    assert not ctx.argv
    assert isinstance(ctx.project_info, dict)
    assert ctx.project_info == {
        "use_openmp": True,
        "use_cuda": True,
        "float_format": "float32",
    }
