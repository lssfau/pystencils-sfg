import sympy as sp

from pystencils import fields, kernel

from pystencilssfg import SourceFileGenerator
from pystencilssfg.lang.cpp.std import mdspan

mdspan.configure(namespace="std::experimental", header="<experimental/mdspan>")

with SourceFileGenerator() as sfg:
    sfg.namespace("gen")

    u_src, u_dst, f = fields("u_src, u_dst, f(1) : double[2D]", layout="fzyx")
    h = sp.Symbol("h")

    @kernel
    def poisson_jacobi():
        u_dst[0, 0] @= (
            h**2 * f[0, 0] + u_src[1, 0] + u_src[-1, 0] + u_src[0, 1] + u_src[0, -1]
        ) / 4

    poisson_kernel = sfg.kernels.create(poisson_jacobi)

    sfg.function("jacobi_smooth")(
        sfg.map_field(u_src, mdspan.from_field(u_src, layout_policy="layout_left")),
        sfg.map_field(u_dst, mdspan.from_field(u_dst, layout_policy="layout_left")),
        sfg.map_field(f, mdspan.from_field(f, layout_policy="layout_left")),
        sfg.call(poisson_kernel),
    )
