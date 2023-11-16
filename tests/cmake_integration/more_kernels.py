# type: ignore

import sympy as sp

from pystencils import fields, kernel, Field

from pystencilssfg import SourceFileGenerator


with SourceFileGenerator() as sfg:
    src: Field = fields("src: double[2D]")

    h = sp.Symbol('h')

    @kernel
    def poisson_gs():
        src[0, 0] @= (src[1, 0] + src[-1, 0] + src[0, 1] + src[0, -1]) / 4

    poisson_kernel = sfg.kernels.create(poisson_gs)

    sfg.function("gs_smooth")(
        sfg.call(poisson_kernel)
    )
