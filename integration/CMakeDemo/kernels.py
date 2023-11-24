# type: ignore

import sympy as sp

from pystencils import fields, kernel

from pystencilssfg import SourceFileGenerator


with SourceFileGenerator() as sfg:
    src, dst = fields("src, dst(1) : double[2D]")

    @kernel
    def poisson_jacobi():
        dst[0, 0] @= (src[1, 0] + src[-1, 0] + src[0, 1] + src[0, -1]) / 4

    poisson_kernel = sfg.kernels.create(poisson_jacobi)

    sfg.function("jacobi_smooth")(
        sfg.call(poisson_kernel)
    )
