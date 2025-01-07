from pystencils import Target, CreateKernelConfig, no_jit
from lbmpy import create_lb_update_rule, LBMOptimisation
from pystencilssfg import SourceFileGenerator, SfgConfig

sfg_config = SfgConfig()
sfg_config.extensions.impl = "cu"
sfg_config.output_directory = "out/test_cuda"
sfg_config.outer_namespace = "gen_code"

with SourceFileGenerator(sfg_config) as sfg:
    gen_config = CreateKernelConfig(target=Target.CUDA, jit=no_jit)
    opt = LBMOptimisation(field_layout="fzyx")
    update = create_lb_update_rule()
    kernel = sfg.kernels.create(update, "lbm_update", gen_config)

    sfg.function("lb_update")(sfg.call(kernel))
