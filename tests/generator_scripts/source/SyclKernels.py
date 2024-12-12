import sympy as sp
import pystencils as ps

from pystencilssfg import SourceFileGenerator, SfgConfig, OutputMode
from pystencilssfg.extensions.sycl import SyclComposer

cfg = SfgConfig()
cfg.output_mode = OutputMode.INLINE
cfg.extensions.impl = "ipp"

with SourceFileGenerator(cfg) as sfg:
    sfg = SyclComposer(sfg)

    u_src, u_dst, f = ps.fields("u_src, u_dst, f: double[10, 10]", layout="fzyx")
    h = sp.Rational(1, 4)

    @ps.kernel
    def poisson_jacobi():
        u_dst[0,0] @= (h**2 * f[0, 0] + u_src[1, 0] + u_src[-1, 0] + u_src[0, 1] + u_src[0, -1]) / 4

    gen_config = ps.CreateKernelConfig(
        target=ps.Target.SYCL
    )

    poisson_kernel = sfg.kernels.create(poisson_jacobi, config=gen_config)

    cgh = sfg.sycl_handler("cgh")
    rang = sfg.sycl_range(2, "range")

    sfg.function("invoke_parallel_for")(
        cgh.parallel_for(rang)(
            sfg.call(poisson_kernel)
        )
    )
