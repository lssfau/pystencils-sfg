from __future__ import annotations

from typing import overload

from pystencils.codegen import GpuKernel, Target
from pystencils.codegen.gpu_indexing import (
    ManualLaunchConfiguration,
    AutomaticLaunchConfiguration,
    DynamicBlockSizeLaunchConfiguration,
)

from .mixin import SfgComposerMixIn
from .basic_composer import make_statements, make_sequence

from ..context import SfgContext
from ..ir import (
    SfgKernelHandle,
    SfgCallTreeNode,
    SfgGpuKernelInvocation,
    SfgBlock,
    SfgSequence,
)
from ..lang import ExprLike, AugExpr
from ..lang.gpu import CudaAPI, HipAPI, ProvidesGpuRuntimeAPI


class SfgGpuComposer(SfgComposerMixIn):
    """Composer mix-in providing methods to generate GPU kernel invocations.

    .. function:: gpu_invoke(kernel_handle: SfgKernelHandle, **kwargs)

        Invoke a GPU kernel with launch configuration parameters depending on its code generator configuration.

        The overloads of this method are listed below.
        They all (partially) mirror the CUDA and HIP ``kernel<<< Gs, Bs, Sm, St >>>()`` syntax;
        for details on the launch configuration arguments,
        refer to `Launch Configurations in CUDA`_
        or `Launch Configurations in HIP`_.

    .. function:: gpu_invoke(kernel_handle: SfgKernelHandle, *, grid_size: ExprLike, block_size: ExprLike, shared_memory_bytes: ExprLike = "0", stream: ExprLike | None = None, ) -> SfgCallTreeNode
        :noindex:

        Invoke a GPU kernel with a manual launch grid.

        Requires that the kernel was generated
        with `manual_launch_grid <pystencils.codegen.config.GpuOptions.manual_launch_grid>`
        set to `True`.

    .. function:: gpu_invoke(self, kernel_handle: SfgKernelHandle, *, shared_memory_bytes: ExprLike = "0", stream: ExprLike | None = None, ) -> SfgCallTreeNode
        :noindex:

        Invoke a GPU kernel with an automatic launch grid.

        This signature accepts kernels generated with an indexing scheme that
        causes the launch grid to be determined automatically,
        such as `Blockwise4D <pystencils.codegen.config.GpuIndexingScheme.Blockwise4D>`.

    .. function:: gpu_invoke(self, kernel_handle: SfgKernelHandle, *, block_size: ExprLike | None = None, shared_memory_bytes: ExprLike = "0", stream: ExprLike | None = None, ) -> SfgCallTreeNode
        :noindex:

        Invoke a GPU kernel with a dynamic launch grid.

        This signature accepts kernels generated with an indexing scheme that permits a user-defined
        blocks size, such as `Linear3D <pystencils.codegen.config.GpuIndexingScheme.Linear3D>`.
        The grid size is calculated automatically by dividing the number of work items in each
        dimension by the block size, rounding up.

    .. _Launch Configurations in CUDA: https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#execution-configuration

    .. _Launch Configurations in HIP: https://rocmdocs.amd.com/projects/HIP/en/latest/how-to/hip_cpp_language_extensions.html#calling-global-functions
    """  # NOQA: E501

    @overload
    def gpu_invoke(
        self,
        kernel_handle: SfgKernelHandle,
        *,
        grid_size: ExprLike,
        block_size: ExprLike,
        shared_memory_bytes: ExprLike = "0",
        stream: ExprLike | None = None,
    ) -> SfgCallTreeNode: ...

    @overload
    def gpu_invoke(
        self,
        kernel_handle: SfgKernelHandle,
        *,
        shared_memory_bytes: ExprLike = "0",
        stream: ExprLike | None = None,
    ) -> SfgCallTreeNode: ...

    @overload
    def gpu_invoke(
        self,
        kernel_handle: SfgKernelHandle,
        *,
        block_size: ExprLike | None = None,
        shared_memory_bytes: ExprLike = "0",
        stream: ExprLike | None = None,
    ) -> SfgCallTreeNode: ...

    def gpu_invoke(
        self,
        kernel_handle: SfgKernelHandle,
        shared_memory_bytes: ExprLike = "0",
        stream: ExprLike | None = None,
        **kwargs,
    ) -> SfgCallTreeNode:
        builder = GpuInvocationBuilder(self._ctx, kernel_handle)
        builder.shared_memory_bytes = shared_memory_bytes
        builder.stream = stream

        return builder(**kwargs)

    def cuda_invoke(
        self,
        kernel_handle: SfgKernelHandle,
        num_blocks: ExprLike,
        threads_per_block: ExprLike,
        stream: ExprLike | None,
    ):
        from warnings import warn

        warn(
            "cuda_invoke is deprecated and will be removed before version 0.1. "
            "Use `gpu_invoke` instead.",
            FutureWarning,
        )

        return self.gpu_invoke(
            kernel_handle,
            grid_size=num_blocks,
            block_size=threads_per_block,
            stream=stream,
        )


class GpuInvocationBuilder:
    def __init__(
        self,
        ctx: SfgContext,
        kernel_handle: SfgKernelHandle,
    ):
        self._ctx = ctx
        self._kernel_handle = kernel_handle

        ker = kernel_handle.kernel

        if not isinstance(ker, GpuKernel):
            raise ValueError(f"Non-GPU kernel was passed to `gpu_invoke`: {ker}")

        launch_config = ker.get_launch_configuration()

        self._launch_config = launch_config

        gpu_api: type[ProvidesGpuRuntimeAPI]
        match ker.target:
            case Target.CUDA:
                gpu_api = CudaAPI
            case Target.HIP:
                gpu_api = HipAPI
            case _:
                assert False, "unexpected GPU target"

        self._gpu_api = gpu_api
        self._dim3 = gpu_api.dim3

        self._shared_memory_bytes: ExprLike = "0"
        self._stream: ExprLike | None = None

    @property
    def shared_memory_bytes(self) -> ExprLike:
        return self._shared_memory_bytes

    @shared_memory_bytes.setter
    def shared_memory_bytes(self, bs: ExprLike):
        self._shared_memory_bytes = bs

    @property
    def stream(self) -> ExprLike | None:
        return self._stream

    @stream.setter
    def stream(self, s: ExprLike | None):
        self._stream = s

    def _render_invocation(
        self, grid_size: ExprLike, block_size: ExprLike
    ) -> SfgSequence:
        stmt_grid_size = make_statements(grid_size)
        stmt_block_size = make_statements(block_size)
        stmt_smem = make_statements(self._shared_memory_bytes)
        stmt_stream = (
            make_statements(self._stream) if self._stream is not None else None
        )

        return make_sequence(
            "/* clang-format off */",
            "/* [pystencils-sfg] Formatting may add illegal spaces between angular brackets in `<<< >>>` */",
            SfgGpuKernelInvocation(
                self._kernel_handle,
                stmt_grid_size,
                stmt_block_size,
                shared_memory_bytes=stmt_smem,
                stream=stmt_stream,
            ),
            "/* clang-format on */",
        )

    def __call__(self, **kwargs: ExprLike) -> SfgCallTreeNode:
        match self._launch_config:
            case ManualLaunchConfiguration():
                return self._invoke_manual(**kwargs)
            case AutomaticLaunchConfiguration():
                return self._invoke_automatic(**kwargs)
            case DynamicBlockSizeLaunchConfiguration():
                return self._invoke_dynamic(**kwargs)
            case _:
                raise ValueError(
                    f"Unexpected launch configuration: {self._launch_config}"
                )

    def _invoke_manual(self, grid_size: ExprLike, block_size: ExprLike):
        assert isinstance(self._launch_config, ManualLaunchConfiguration)
        return self._render_invocation(grid_size, block_size)

    def _invoke_automatic(self):
        assert isinstance(self._launch_config, AutomaticLaunchConfiguration)

        from .composer import SfgComposer

        sfg = SfgComposer(self._ctx)

        grid_size_entries = [
            self._to_uint32_t(sfg.expr_from_lambda(gs))
            for gs in self._launch_config._grid_size
        ]
        grid_size_var = self._dim3(const=True).var("__grid_size")

        block_size_entries = [
            self._to_uint32_t(sfg.expr_from_lambda(bs))
            for bs in self._launch_config._block_size
        ]
        block_size_var = self._dim3(const=True).var("__block_size")

        nodes = [
            sfg.init(grid_size_var)(*grid_size_entries),
            sfg.init(block_size_var)(*block_size_entries),
            self._render_invocation(grid_size_var, block_size_var),
        ]

        return SfgBlock(SfgSequence(nodes))

    def _invoke_dynamic(self, block_size: ExprLike | None = None):
        assert isinstance(self._launch_config, DynamicBlockSizeLaunchConfiguration)

        from .composer import SfgComposer

        sfg = SfgComposer(self._ctx)

        block_size_init_args: tuple[ExprLike, ...]
        if block_size is None:
            block_size_init_args = tuple(
                str(bs) for bs in self._launch_config.default_block_size
            )
        else:
            block_size_init_args = (block_size,)

        block_size_var = self._dim3(const=True).var("__block_size")

        from ..lang.cpp import std

        work_items_entries = [
            sfg.expr_from_lambda(wit) for wit in self._launch_config.num_work_items
        ]
        work_items_var = std.tuple("uint32_t", "uint32_t", "uint32_t", const=True).var(
            "__work_items"
        )

        def _div_ceil(a: ExprLike, b: ExprLike):
            return AugExpr.format("({a} + {b} - 1) / {b}", a=a, b=b)

        grid_size_entries = [
            _div_ceil(work_items_var.get(i), bs)
            for i, bs in enumerate(
                [
                    block_size_var.x,
                    block_size_var.y,
                    block_size_var.z,
                ]
            )
        ]
        grid_size_var = self._dim3(const=True).var("__grid_size")

        nodes = [
            sfg.init(block_size_var)(*block_size_init_args),
            sfg.init(work_items_var)(*work_items_entries),
            sfg.init(grid_size_var)(*grid_size_entries),
            self._render_invocation(grid_size_var, block_size_var),
        ]

        return SfgBlock(SfgSequence(nodes))

    @staticmethod
    def _to_uint32_t(expr: AugExpr) -> AugExpr:
        return AugExpr("uint32_t").format("uint32_t({})", expr)
