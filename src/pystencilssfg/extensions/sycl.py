from __future__ import annotations
from typing import Sequence
from enum import Enum
import re

from pystencils.types import UserTypeSpec, PsType, PsCustomType, create_type
from pystencils import Target

from pystencilssfg.composer.basic_composer import SequencerArg

from ..config import CodeStyle
from ..exceptions import SfgException
from ..context import SfgContext
from ..composer import (
    SfgBasicComposer,
    SfgClassComposer,
    SfgComposer,
    SfgComposerMixIn,
    make_sequence,
)
from ..ir import (
    SfgKernelHandle,
    SfgCallTreeNode,
    SfgCallTreeLeaf,
    SfgKernelCallNode,
)

from ..lang import SfgVar, AugExpr, cpptype, Ref, VarLike, _VarLike, asvar
from ..lang.cpp.sycl_accessor import SyclAccessor


accessor = SyclAccessor


class SyclComposerMixIn(SfgComposerMixIn):
    """Composer mix-in for SYCL code generation"""

    def sycl_handler(self, name: str) -> SyclHandler:
        """Obtain a `SyclHandler`, which represents a ``sycl::handler`` object."""
        return SyclHandler(self._ctx).var(name)

    def sycl_group(self, dims: int, name: str) -> SyclGroup:
        """Obtain a `SyclHandler`, which represents a ``sycl::handler`` object."""
        return SyclGroup(dims, self._ctx).var(name)

    def sycl_range(self, dims: int, name: str, ref: bool = False) -> SyclRange:
        return SyclRange(dims, ref=ref).var(name)


class SyclComposer(SfgBasicComposer, SfgClassComposer, SyclComposerMixIn):
    """Composer extension providing SYCL code generation capabilities"""

    def __init__(self, sfg: SfgContext | SfgComposer):
        super().__init__(sfg)


class SyclRange(AugExpr):
    _template = cpptype("sycl::range< {dims} >", "<sycl/sycl.hpp>")

    def __init__(self, dims: int, const: bool = False, ref: bool = False):
        dtype = self._template(dims=dims, const=const, ref=ref)
        super().__init__(dtype)


class SyclHandler(AugExpr):
    """Represents a SYCL command group handler (``sycl::handler``)."""

    _type = cpptype("sycl::handler", "<sycl/sycl.hpp>")

    def __init__(self, ctx: SfgContext):
        dtype = Ref(self._type())
        super().__init__(dtype)

        self._ctx = ctx

    def parallel_for(
        self,
        range: VarLike | Sequence[int],
    ):
        """Generate a ``parallel_for`` kernel invocation using this command group handler.
        The syntax of this uses a chain of two calls to mimic C++ syntax:

        .. code-block:: Python

            sfg.parallel_for(range)(
                # Body
            )

        The body is constructed via sequencing (see `make_sequence`).

        Args:
            range: Object, or tuple of integers, indicating the kernel's iteration range
        """
        if isinstance(range, _VarLike):
            range = asvar(range)

        def check_kernel(khandle: SfgKernelHandle):
            kfunc = khandle.kernel
            if kfunc.target != Target.SYCL:
                raise SfgException(
                    f"Kernel given to `parallel_for` is no SYCL kernel: {khandle.fqname}"
                )

        id_regex = re.compile(r"sycl::(id|item|nd_item)<\s*[0-9]\s*>")

        def filter_id(param: SfgVar) -> bool:
            return (
                isinstance(param.dtype, PsCustomType)
                and id_regex.search(param.dtype.c_string()) is not None
            )

        def sequencer(*args: SequencerArg):
            id_param = []
            for arg in args:
                if isinstance(arg, SfgKernelCallNode):
                    check_kernel(arg._kernel_handle)
                    id_param.append(
                        list(filter(filter_id, arg._kernel_handle.scalar_parameters))[0]
                    )

            if not all(item == id_param[0] for item in id_param):
                raise ValueError(
                    "id_param should be the same for all kernels in parallel_for"
                )
            tree = make_sequence(*args)

            kernel_lambda = SfgLambda(("=",), (id_param[0],), tree, None)
            return SyclKernelInvoke(
                self, SyclInvokeType.ParallelFor, range, kernel_lambda
            )

        return sequencer


class SyclGroup(AugExpr):
    """Represents a SYCL group (``sycl::group``)."""

    _template = cpptype("sycl::group< {dims} >", "<sycl/sycl.hpp>")

    def __init__(self, dimensions: int, ctx: SfgContext):
        dtype = Ref(self._template(dims=dimensions))
        super().__init__(dtype)

        self._dimensions = dimensions
        self._ctx = ctx

    def parallel_for_work_item(
        self, range: VarLike | Sequence[int], khandle: SfgKernelHandle
    ):
        """Generate a ``parallel_for_work_item` kernel invocation on this group.`

        Args:
            range: Object, or tuple of integers, indicating the kernel's iteration range
            kernel: Handle to the pystencils-kernel to be executed
        """
        if isinstance(range, _VarLike):
            range = asvar(range)

        kfunc = khandle.kernel
        if kfunc.target != Target.SYCL:
            raise SfgException(
                f"Kernel given to `parallel_for` is no SYCL kernel: {khandle.fqname}"
            )

        id_regex = re.compile(r"sycl::id<\s*[0-9]\s*>")

        def filter_id(param: SfgVar) -> bool:
            return (
                isinstance(param.dtype, PsCustomType)
                and id_regex.search(param.dtype.c_string()) is not None
            )

        id_param = list(filter(filter_id, khandle.scalar_parameters))[0]
        h_item = SfgVar("item", PsCustomType("sycl::h_item< 3 >"))

        comp = SfgComposer(self._ctx)
        tree = comp.seq(
            comp.set_param(id_param, AugExpr.format("{}.get_local_id()", h_item)),
            SfgKernelCallNode(khandle),
        )

        kernel_lambda = SfgLambda(("=",), (h_item,), tree, None)
        invoke = SyclKernelInvoke(
            self, SyclInvokeType.ParallelForWorkItem, range, kernel_lambda
        )
        return invoke


class SfgLambda:
    """Models a C++ lambda expression"""

    def __init__(
        self,
        captures: Sequence[str],
        params: Sequence[SfgVar],
        tree: SfgCallTreeNode,
        return_type: UserTypeSpec | None = None,
    ) -> None:
        self._captures = tuple(captures)
        self._params = tuple(params)
        self._tree = tree
        self._return_type: PsType | None = (
            create_type(return_type) if return_type is not None else None
        )

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

    def get_code(self, cstyle: CodeStyle):
        captures = ", ".join(self._captures)
        params = ", ".join(f"{p.dtype.c_string()} {p.name}" for p in self._params)
        body = self._tree.get_code(cstyle)
        body = cstyle.indent(body)
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

        self._required_params = set(invoker.depends | lamb.required_parameters)

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

    def get_code(self, cstyle: CodeStyle) -> str:
        if isinstance(self._range, SfgVar):
            range_code = self._range.name
        else:
            range_code = "{ " + ", ".join(str(r) for r in self._range) + " }"

        kernel_code = self._lambda.get_code(cstyle)
        invoker = str(self._invoker)
        method = self._invoke_type.method

        return f"{invoker}.{method}({range_code}, {kernel_code});"
