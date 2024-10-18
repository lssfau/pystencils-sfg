from __future__ import annotations
from typing import Sequence
from enum import Enum
import re

from pystencils.types import PsType, PsCustomType
from pystencils.enums import Target
from pystencils.backend.kernelfunction import KernelParameter

from ..exceptions import SfgException
from ..context import SfgContext
from ..composer import (
    SfgBasicComposer,
    SfgClassComposer,
    SfgComposer,
    SfgComposerMixIn,
)
from ..ir.source_components import SfgKernelHandle, SfgHeaderInclude
from ..ir.source_components import SfgSymbolLike
from ..ir import (
    SfgCallTreeNode,
    SfgCallTreeLeaf,
    SfgKernelCallNode,
)

from ..lang import SfgVar, AugExpr


class SyclComposerMixIn(SfgComposerMixIn):
    """Composer mix-in for SYCL code generation"""

    def sycl_handler(self, name: str) -> SyclHandler:
        """Obtain a `SyclHandler`, which represents a ``sycl::handler`` object."""
        return SyclHandler(self._ctx).var(name)

    def sycl_group(self, dims: int, name: str) -> SyclGroup:
        """Obtain a `SyclHandler`, which represents a ``sycl::handler`` object."""
        return SyclGroup(dims, self._ctx).var(name)

    def sycl_range(self, dims: int, name: str, ref: bool = False) -> SfgVar:
        ref_str = " &" if ref else ""
        return SfgVar(name, PsCustomType(f"sycl::range< {dims} >{ref_str}"))


class SyclComposer(SfgBasicComposer, SfgClassComposer, SyclComposerMixIn):
    """Composer extension providing SYCL code generation capabilities"""

    def __init__(self, sfg: SfgContext | SfgComposer):
        super().__init__(sfg)


class SyclHandler(AugExpr):
    """Represents a SYCL command group handler (``sycl::handler``)."""

    def __init__(self, ctx: SfgContext):
        dtype = PsCustomType("sycl::handler &")
        super().__init__(dtype)

        self._ctx = ctx

    def parallel_for(self, range: SfgVar | Sequence[int], kernel: SfgKernelHandle):
        """Generate a ``parallel_for`` kernel invocation using this command group handler.

        Args:
            range: Object, or tuple of integers, indicating the kernel's iteration range
            kernel: Handle to the pystencils-kernel to be executed
        """
        self._ctx.add_include(SfgHeaderInclude("sycl/sycl.hpp", system_header=True))

        kfunc = kernel.get_kernel_function()
        if kfunc.target != Target.SYCL:
            raise SfgException(
                f"Kernel given to `parallel_for` is no SYCL kernel: {kernel.kernel_name}"
            )

        id_regex = re.compile(r"sycl::(id|item|nd_item)<\s*[0-9]\s*>")

        def filter_id(param: SfgSymbolLike[KernelParameter]) -> bool:
            return (
                isinstance(param.dtype, PsCustomType)
                and id_regex.search(param.dtype.c_string()) is not None
            )

        id_param = list(filter(filter_id, kernel.scalar_parameters))[0]

        tree = SfgKernelCallNode(kernel)

        kernel_lambda = SfgLambda(("=",), (id_param,), tree, None)
        return SyclKernelInvoke(self, SyclInvokeType.ParallelFor, range, kernel_lambda)


class SyclGroup(AugExpr):
    """Represents a SYCL group (``sycl::group``)."""

    def __init__(self, dimensions: int, ctx: SfgContext):
        dtype = PsCustomType(f"sycl::group< {dimensions} > &")
        super().__init__(dtype)

        self._dimensions = dimensions
        self._ctx = ctx

    def parallel_for_work_item(
        self, range: SfgVar | Sequence[int], kernel: SfgKernelHandle
    ):
        """Generate a ``parallel_for_work_item` kernel invocation on this group.`

        Args:
            range: Object, or tuple of integers, indicating the kernel's iteration range
            kernel: Handle to the pystencils-kernel to be executed
        """

        self._ctx.add_include(SfgHeaderInclude("sycl/sycl.hpp", system_header=True))

        kfunc = kernel.get_kernel_function()
        if kfunc.target != Target.SYCL:
            raise SfgException(
                f"Kernel given to `parallel_for` is no SYCL kernel: {kernel.kernel_name}"
            )

        id_regex = re.compile(r"sycl::id<\s*[0-9]\s*>")

        def filter_id(param: SfgSymbolLike[KernelParameter]) -> bool:
            return (
                isinstance(param.dtype, PsCustomType)
                and id_regex.search(param.dtype.c_string()) is not None
            )

        id_param = list(filter(filter_id, kernel.scalar_parameters))[0]
        h_item = SfgVar("item", PsCustomType("sycl::h_item< 3 >"))

        comp = SfgComposer(self._ctx)
        tree = comp.seq(
            comp.map_param(
                id_param,
                h_item,
                f"{id_param.dtype} {id_param.name} = {h_item}.get_local_id();",
            ),
            SfgKernelCallNode(kernel),
        )

        kernel_lambda = SfgLambda(("=",), (h_item,), tree, None)
        return SyclKernelInvoke(
            self, SyclInvokeType.ParallelForWorkItem, range, kernel_lambda
        )


class SfgLambda:
    """Models a C++ lambda expression"""

    def __init__(
        self,
        captures: Sequence[str],
        params: Sequence[SfgVar],
        tree: SfgCallTreeNode,
        return_type: PsType | None = None,
    ) -> None:
        self._captures = tuple(captures)
        self._params = tuple(params)
        self._tree = tree
        self._return_type = return_type

        from ..ir.postprocessing import CallTreePostProcessing

        postprocess = CallTreePostProcessing()
        self._required_params = postprocess(self._tree).function_params - set(
            self._params
        )

    @property
    def captures(self) -> tuple[str, ...]:
        return self._captures

    @property
    def parameters(self) -> tuple[SfgVar, ...]:
        return self._params

    @property
    def body(self) -> SfgCallTreeNode:
        return self._tree

    @property
    def return_type(self) -> PsType | None:
        return self._return_type

    @property
    def required_parameters(self) -> set[SfgVar]:
        return self._required_params

    def get_code(self, ctx: SfgContext):
        captures = ", ".join(self._captures)
        params = ", ".join(f"{p.dtype} {p.name}" for p in self._params)
        body = self._tree.get_code(ctx)
        body = ctx.codestyle.indent(body)
        rtype = (
            f"-> {self._return_type.c_string()} "
            if self._return_type is not None
            else ""
        )

        return f"[{captures}] ({params}) {rtype}{{\n{body}\n}}"


class SyclInvokeType(Enum):
    ParallelFor = ("parallel_for", SyclHandler)
    ParallelForWorkItem = ("parallel_for_work_item", SyclGroup)

    @property
    def method(self) -> str:
        return self.value[0]

    @property
    def invoker_class(self) -> type:
        return self.value[1]


class SyclKernelInvoke(SfgCallTreeLeaf):
    """A SYCL kernel invocation on a given handler or group"""

    def __init__(
        self,
        invoker: SyclHandler | SyclGroup,
        invoke_type: SyclInvokeType,
        range: SfgVar | Sequence[int],
        lamb: SfgLambda,
    ):
        if not isinstance(invoker, invoke_type.invoker_class):
            raise SfgException(
                f"Cannot invoke kernel via `{invoke_type.method}` on a {type(invoker)}"
            )

        super().__init__()
        self._invoker = invoker
        self._invoke_type = invoke_type
        self._range: SfgVar | tuple[int, ...] = (
            range if isinstance(range, SfgVar) else tuple(range)
        )
        self._lambda = lamb

        self._required_params = invoker.depends | lamb.required_parameters

        if isinstance(range, SfgVar):
            self._required_params.add(range)

    @property
    def invoker(self) -> SyclHandler | SyclGroup:
        return self._invoker

    @property
    def range(self) -> SfgVar | tuple[int, ...]:
        return self._range

    @property
    def kernel(self) -> SfgLambda:
        return self._lambda

    @property
    def depends(self) -> set[SfgVar]:
        return self._required_params

    def get_code(self, ctx: SfgContext) -> str:
        if isinstance(self._range, SfgVar):
            range_code = self._range.name
        else:
            range_code = "{ " + ", ".join(str(r) for r in self._range) + " }"

        kernel_code = self._lambda.get_code(ctx)
        invoker = str(self._invoker)
        method = self._invoke_type.method

        return f"{invoker}.{method}({range_code}, {kernel_code});"
