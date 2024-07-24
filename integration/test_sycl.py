from pystencils import Target, CreateKernelConfig, create_kernel, no_jit
from lbmpy import create_lb_update_rule, LBMOptimisation
from pystencilssfg import SourceFileGenerator, SfgConfiguration, SfgOutputMode
from pystencilssfg.lang.cpp import mdspan_ref

sfg_config = SfgConfiguration(
    output_directory="out/test_sycl",
    outer_namespace="gen_code",
    impl_extension="ipp",
    output_mode=SfgOutputMode.INLINE
)

with SourceFileGenerator(sfg_config) as sfg:
    gen_config = CreateKernelConfig(target=Target.SYCL, jit=no_jit)
    opt = LBMOptimisation(field_layout="fzyx")
    update = create_lb_update_rule()
    kernel = sfg.kernels.create(update, "lbm_update", gen_config)

    sfg.function("lb_update")(
        sfg.call(kernel)
    )
