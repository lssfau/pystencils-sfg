import pystencils as ps
import sympy as sp

from pystencilssfg import SourceFileGenerator
from pystencilssfg.lang.cpp import std


with SourceFileGenerator() as sfg:
    sfg.namespace("StlContainers1D::gen")

    src, dst = ps.fields("src, dst: double[1D]")

    asms = [ps.Assignment(dst[0], sp.Rational(1, 3) * (src[-1] + src[0] + src[1]))]

    kernel = sfg.kernels.create(asms, "average")

    sfg.function("averageVector")(
        sfg.map_field(src, std.vector.from_field(src)),
        sfg.map_field(dst, std.vector.from_field(dst)),
        sfg.call(kernel),
    )

    sfg.function("averageSpan")(
        sfg.map_field(src, std.span.from_field(src)),
        sfg.map_field(dst, std.span.from_field(dst)),
        sfg.call(kernel),
    )
