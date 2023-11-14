import sympy as sp
import numpy as np

from pystencils.session import *

from pystencilssfg import SourceFileGenerator
from pystencilssfg.source_concepts.cpp import std_mdspan


with SourceFileGenerator("poisson") as sfg:
    src, dst = ps.fields("src, dst(1) : double[2D]")

    h = sp.Symbol('h')

    @ps.kernel
    def poisson_jacobi():
        dst[0,0] @= (src[1, 0] + src[-1, 0] + src[0, 1] + src[0, -1]) / 4

    poisson_kernel = sfg.kernels.create(poisson_jacobi)

    sfg.function("jacobi_smooth")(
        sfg.call(poisson_kernel)
    )
