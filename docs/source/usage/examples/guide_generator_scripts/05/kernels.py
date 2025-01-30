from pystencilssfg import SourceFileGenerator

import pystencils as ps
import sympy as sp

with SourceFileGenerator() as sfg:
    #   Define a copy kernel
    src, dst = ps.fields("src, dst: double[1D]")
    c = sp.Symbol("c")

    @ps.kernel
    def scale():
        dst.center @= c * src.center()

    #   Add it to the file
    scale_kernel = sfg.kernels.create(scale, "scale")

    #   start
    import pystencilssfg.lang.cpp.std as std

    sfg.include("<span>")

    sfg.function("scale_kernel")(
        sfg.map_field(src, std.vector.from_field(src)),
        sfg.map_field(dst, std.span.from_field(dst)),
        sfg.call(scale_kernel)
    )
    #   end
