from pystencilssfg import SourceFileGenerator, SfgConfig
from pystencilssfg.lang.cpp import std
import pystencils as ps

cfg = SfgConfig(header_only=True)

with SourceFileGenerator(cfg) as sfg:
    n = sfg.var("n", "int32")

    #   Should be automatically marked inline
    sfg.function("twice").returns("int32")(
        sfg.expr("return 2 * {};", n)
    )

    #   Inline kernel

    arr = ps.fields("arr: int64[1D]")
    vec = std.vector.from_field(arr)

    c = ps.TypedSymbol("c", "int64")

    asm = ps.Assignment(arr(0), c * arr(0))
    khandle = sfg.kernels.create(asm)

    sfg.function("twiceKernel")(
        sfg.map_field(arr, vec),
        sfg.set_param(c, "2"),
        sfg.call(khandle)
    )

    #   Inline class members

    sfg.klass("ScaleKernel")(
        sfg.private(
            c
        ),
        sfg.public(
            sfg.constructor(c).init(c)(c),
            sfg.method("operator()")(
                sfg.map_field(arr, vec),
                sfg.set_param(c, "this->c"),
                sfg.call(khandle)
            )
        )
    )
