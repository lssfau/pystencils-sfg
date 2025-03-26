from pystencilssfg import SourceFileGenerator
from pystencilssfg.lang.cpp import std
import pystencils as ps
import sympy as sp

std.mdspan.configure(namespace="std::experimental", header="<experimental/mdspan>")

with SourceFileGenerator() as sfg:
    sfg.namespace("gen")

    u_field = ps.fields("u(3): double[2D]", layout="c")
    u = sp.symbols("u_:3")

    asms = [ps.Assignment(u_field(i), u[i]) for i in range(3)]
    ker = sfg.kernels.create(asms)

    sfg.function("invoke")(
        sfg.map_field(u_field, std.mdspan.from_field(u_field, layout_policy="layout_right")),
        sfg.map_vector(u, std.vector("double", const=True, ref=True).var("vel")),
        sfg.call(ker)
    )
