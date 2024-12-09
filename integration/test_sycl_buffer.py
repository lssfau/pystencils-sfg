from pystencils import Target, CreateKernelConfig, no_jit
from lbmpy import create_lb_update_rule, LBMOptimisation
from pystencilssfg import SourceFileGenerator, SfgConfig, OutputMode
from pystencilssfg.lang.cpp.sycl_accessor import sycl_accessor_ref
import pystencilssfg.extensions.sycl as sycl
from itertools import chain

sfg_config = SfgConfig(
    output_directory="out/test_sycl_buffer",
    outer_namespace="gen_code",
    output_mode=OutputMode.INLINE,
)

with SourceFileGenerator(sfg_config) as sfg:
    sfg = sycl.SyclComposer(sfg)
    gen_config = CreateKernelConfig(target=Target.SYCL, jit=no_jit)
    opt = LBMOptimisation(field_layout="fzyx")
    update = create_lb_update_rule(lbm_optimisation=opt)
    kernel = sfg.kernels.create(update, "lbm_update", gen_config)

    cgh = sfg.sycl_handler("handler")
    rang = sfg.sycl_range(update.method.dim, "range")
    mappings = [
        sfg.map_field(field, sycl_accessor_ref(field))
        for field in chain(update.free_fields, update.bound_fields)
    ]

    sfg.function("lb_update")(
        cgh.parallel_for(rang)(
            *mappings,
            sfg.call(kernel),
        ),
    )
