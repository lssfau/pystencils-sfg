import sympy as sp

from pystencils import fields, kernel

from pystencilssfg import SourceFileGenerator
from pystencilssfg.source_concepts.cpp import mdspan_ref

with SourceFileGenerator() as sfg:
    u_src, u_dst, f = fields("u_src, u_dst, f(1) : double[2D]", layout="fzyx")
    h = sp.Symbol("h")

    @kernel
    def poisson_jacobi():
        u_dst[0,0] @= (h**2 * f[0, 0] * u_src[1, 0] + u_src[-1, 0] + u_src[0, 1] + u_src[0, -1]) / 4

    poisson_kernel = sfg.kernels.create(poisson_jacobi)

    sfg.function("jacobi_smooth")(
        sfg.map_field(u_src, mdspan_ref(u_src)),
        sfg.map_field(u_dst, mdspan_ref(u_dst)),
        sfg.map_field(f, mdspan_ref(f)),
        sfg.call(poisson_kernel)
    )
