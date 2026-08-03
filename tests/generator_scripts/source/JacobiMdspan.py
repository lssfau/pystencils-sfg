import sympy as sp
import pystencils as ps

from pystencilssfg import SourceFileGenerator
from pystencilssfg.lang.cpp.std import mdspan

mdspan.configure(namespace="std::experimental", header="<experimental/mdspan>")

with SourceFileGenerator() as sfg:
    sfg.namespace("gen")

    u_src = ps.grids.TensorField("u_src", 2, (), dtype="double", layout="fzyx")
    u_dst = ps.grids.TensorField("u_dst", 2, (), dtype="double", layout="fzyx")
    f = ps.grids.TensorField("f", 2, (), dtype="double", layout="fzyx")
    h = sp.Symbol("h")

    @ps.flow.operator(iteration_slice=ps.make_slice[1:-1, 1:-1])
    def poisson_jacobi(_eq):
        _eq.store[u_dst()] = (
            h**2 * f[0, 0]()
            + u_src[1, 0]()
            + u_src[-1, 0]()
            + u_src[0, 1]()
            + u_src[0, -1]()
        ) / 4

    poisson_kernel = sfg.kernels.add(poisson_jacobi)

    sfg.function("jacobi_smooth")(
        sfg.map_field(u_src, mdspan.from_field(u_src)),
        sfg.map_field(u_dst, mdspan.from_field(u_dst)),
        sfg.map_field(f, mdspan.from_field(f)),
        sfg.call(poisson_kernel),
    )
