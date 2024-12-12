import pystencils as ps
import sympy as sp
from pystencilssfg import SourceFileGenerator
import pystencilssfg.extensions.sycl as sycl


with SourceFileGenerator() as sfg:
    sfg = sycl.SyclComposer(sfg)
    sfg.namespace("gen")

    u_src, u_dst, f = ps.fields("u_src, u_dst, f : double[2D]", layout="fzyx")
    h = sp.Symbol("h")

    jacobi_update = [
        ps.Assignment(
            u_dst.center(),
            (h**2 * f[0, 0] + u_src[1, 0] + u_src[-1, 0] + u_src[0, 1] + u_src[0, -1])
            / 4,
        )
    ]

    kernel_config = ps.CreateKernelConfig(target=ps.Target.SYCL)
    jacobi_kernel = sfg.kernels.create(jacobi_update, config=kernel_config)

    cgh = sfg.sycl_handler("handler")
    rang = sfg.sycl_range(2, "range")
    mappings = [
        sfg.map_field(u_src, sycl.accessor.from_field(u_src)),
        sfg.map_field(u_dst, sycl.accessor.from_field(u_dst)),
        sfg.map_field(f, sycl.accessor.from_field(f)),
    ]

    sfg.function("jacobiUpdate")(
        cgh.parallel_for(rang)(*mappings, sfg.call(jacobi_kernel)),
    )
