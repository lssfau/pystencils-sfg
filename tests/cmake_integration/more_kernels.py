import sympy as sp
import numpy as np

from pystencils.session import *

from pystencilssfg import SourceFileGenerator
from pystencilssfg.source_concepts.cpp import std_mdspan


with SourceFileGenerator() as sfg:
    src = ps.fields("src: double[2D]")

    h = sp.Symbol('h')

    @ps.kernel
    def poisson_gs():
        src[0,0] @= (src[1, 0] + src[-1, 0] + src[0, 1] + src[0, -1]) / 4

    poisson_kernel = sfg.kernels.create(poisson_gs)

    sfg.function("gs_smooth")(
        sfg.call(poisson_kernel)
    )
