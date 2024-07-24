from pystencilssfg import SourceFileGenerator, SfgComposer

from lbmpy.advanced_streaming import Timestep
from lbmpy import LBMConfig, create_lb_ast

with SourceFileGenerator() as ctx:
    sfg = SfgComposer(ctx)

    lb_config = LBMConfig(streaming_pattern='esotwist')

    lb_ast_even = create_lb_ast(lbm_config=lb_config, timestep=Timestep.EVEN)

    lb_ast_odd = create_lb_ast(lbm_config=lb_config, timestep=Timestep.ODD)

    kernel_even = sfg.kernels.add(lb_ast_even, "lb_even")
    kernel_odd = sfg.kernels.add(lb_ast_odd, "lb_odd")

    sfg.function("myFunction")(
        sfg.branch("(timestep & 1) ^ 1")(
            sfg.call(kernel_even)
        )(
            sfg.call(kernel_odd)
        )
    )
