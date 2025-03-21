from pystencilssfg import SourceFileGenerator
from pystencilssfg.lang.cpp import std
from pystencilssfg.lang.gpu import hip

import pystencils as ps

std.mdspan.configure(namespace="std::experimental", header="<experimental/mdspan>")


src, dst = ps.fields("src, dst: double[3D]", layout="c")
asm = ps.Assignment(dst(0), 2 * src(0))


with SourceFileGenerator() as sfg:
    sfg.namespace("gen")

    base_config = ps.CreateKernelConfig(target=ps.Target.HIP)

    block_size = hip.dim3().var("blockSize")
    grid_size = hip.dim3().var("gridSize")
    stream = hip.stream_t().var("stream")

    with sfg.namespace("linear3d"):
        cfg = base_config.copy()
        cfg.gpu.indexing_scheme = "linear3d"
        khandle = sfg.kernels.create(asm, "scale", cfg)

        sfg.function("scaleKernel")(
            sfg.map_field(
                src, std.mdspan.from_field(src, ref=True, layout_policy="layout_right")
            ),
            sfg.map_field(
                dst, std.mdspan.from_field(dst, ref=True, layout_policy="layout_right")
            ),
            sfg.gpu_invoke(khandle, block_size=block_size, stream=stream),
        )

    with sfg.namespace("linear3d_automatic"):
        cfg = base_config.copy()
        cfg.gpu.indexing_scheme = "linear3d"
        khandle = sfg.kernels.create(asm, "scale", cfg)

        sfg.function("scaleKernel")(
            sfg.map_field(
                src, std.mdspan.from_field(src, ref=True, layout_policy="layout_right")
            ),
            sfg.map_field(
                dst, std.mdspan.from_field(dst, ref=True, layout_policy="layout_right")
            ),
            sfg.gpu_invoke(khandle, stream=stream),
        )

    with sfg.namespace("blockwise4d"):
        cfg = base_config.copy()
        cfg.gpu.indexing_scheme = "blockwise4d"
        khandle = sfg.kernels.create(asm, "scale", cfg)

        sfg.function("scaleKernel")(
            sfg.map_field(
                src, std.mdspan.from_field(src, ref=True, layout_policy="layout_right")
            ),
            sfg.map_field(
                dst, std.mdspan.from_field(dst, ref=True, layout_policy="layout_right")
            ),
            sfg.gpu_invoke(khandle, stream=stream),
        )

    with sfg.namespace("linear3d_manual"):
        cfg = base_config.copy()
        cfg.gpu.indexing_scheme = "linear3d"
        cfg.gpu.manual_launch_grid = True
        khandle = sfg.kernels.create(asm, "scale", cfg)

        sfg.function("scaleKernel")(
            sfg.map_field(
                src, std.mdspan.from_field(src, ref=True, layout_policy="layout_right")
            ),
            sfg.map_field(
                dst, std.mdspan.from_field(dst, ref=True, layout_policy="layout_right")
            ),
            sfg.gpu_invoke(
                khandle, block_size=block_size, grid_size=grid_size, stream=stream
            ),
        )

    with sfg.namespace("blockwise4d_manual"):
        cfg = base_config.copy()
        cfg.gpu.indexing_scheme = "blockwise4d"
        cfg.gpu.manual_launch_grid = True
        khandle = sfg.kernels.create(asm, "scale", cfg)

        sfg.function("scaleKernel")(
            sfg.map_field(
                src, std.mdspan.from_field(src, ref=True, layout_policy="layout_right")
            ),
            sfg.map_field(
                dst, std.mdspan.from_field(dst, ref=True, layout_policy="layout_right")
            ),
            sfg.gpu_invoke(
                khandle, block_size=block_size, grid_size=grid_size, stream=stream
            ),
        )
