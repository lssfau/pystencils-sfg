import sympy as sp
import numpy as np

from pystencils.session import *

from pystencilssfg import SourceFileGenerator
from pystencilssfg.source_concepts.cpp import std_mdspan

def field_t(field: ps.Field):
    return std_mdspan(field.name,
                      field.dtype,
                      (std_mdspan.dynamic_extent, std_mdspan.dynamic_extent),
                      extents_type=np.uint32,
                      reference=True)


with SourceFileGenerator("poisson") as sfg:
    src, dst = ps.fields("src, dst(1) : double[2D]")

    h = sp.Symbol('h')

    @ps.kernel
    def poisson_jacobi():
        dst[0,0] @= (src[1, 0] + src[-1, 0] + src[0, 1] + src[0, -1]) / 4

    poisson_kernel = sfg.kernels.create(poisson_jacobi)

    sfg.function("jacobi_smooth")(
        sfg.map_field(src, field_t(src)),
        sfg.map_field(dst, field_t(dst)),
        sfg.call(poisson_kernel)
    )
