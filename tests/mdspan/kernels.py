import numpy as np
from pystencils.session import *

from pystencilssfg import SourceFileGenerator
from pystencilssfg.source_concepts.cpp.std_mdspan import std_mdspan

with SourceFileGenerator() as sfg:
    src, dst = ps.fields("src, dst(1) : double[2D]")

    @ps.kernel
    def poisson_gs():
        dst[0,0] @= src[1, 0] + src[-1, 0] + src[0, 1] + src[0, -1] - 4 * src[0, 0]

    sfg.include("<iostream>")

    poisson_kernel = sfg.kernels.create(poisson_gs)

    sfg.function("myFunction")(
        sfg.map_field(src, std_mdspan(src.name, np.float64, (std_mdspan.dynamic_extent, std_mdspan.dynamic_extent, 1))),
        sfg.map_field(dst, std_mdspan(dst.name, np.float64, (2, 2, 1))),
        sfg.call(poisson_kernel)
    )
