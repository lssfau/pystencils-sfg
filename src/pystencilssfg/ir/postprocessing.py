from __future__ import annotations
from typing import Sequence, Iterable
import warnings
from dataclasses import dataclass

from abc import ABC, abstractmethod

import sympy as sp

from pystencils import Field
from pystencils.types import deconstify, PsType
from pystencils.codegen.properties import FieldBasePtr, FieldShape, FieldStride

from ..exceptions import SfgException
from ..config import CodeStyle

from .call_tree import SfgCallTreeNode, SfgSequence, SfgStatements
from ..lang.expressions import SfgKernelParamVar
from ..lang import (
    SfgVar,
    SupportsFieldExtraction,
    SupportsVectorExtraction,
    ExprLike,
    AugExpr,
    depends,
    includes,
)


class PostProcessingContext:
    def __init__(self) -> None:
        self._live_variables: dict[str, SfgVar] = dict()

    @property
    def live_variables(self) -> set[SfgVar]:
        return set(self._live_variables.values())

    def get_live_variable(self, name: str) -> SfgVar | None:
        return self._live_variables.get(name)

    def _define(self, vars: Iterable[SfgVar], expr: str):
        for var in vars:
            if var.name in self._live_variables:
                live_var = self._live_variables[var.name]

                live_var_dtype = live_var.dtype
                def_dtype = var.dtype

                #   A const definition conflicts with a non-const live variable
                #   A non-const definition is always OK, but then the types must be the same
                if (def_dtype.const and not live_var_dtype.const) or (
                    deconstify(def_dtype) != deconstify(live_var_dtype)
                ):
                    warnings.warn(
                        f"Type conflict at variable definition: Expected type {live_var_dtype}, but got {def_dtype}.\n"
                        f"    * At definition {expr}",
                        UserWarning,
                    )

                del self._live_variables[var.name]

    def _use(self, vars: Iterable[SfgVar]):
        for var in vars:
            if var.name in self._live_variables:
                live_var = self._live_variables[var.name]

                if var != live_var:
                    if var.dtype == live_var.dtype:
                        #   This can only happen if the variables are SymbolLike,
                        #   i.e. wrap a field-associated kernel parameter
                        #   TODO: Once symbol properties are a thing, check and combine them here
                        warnings.warn(
                            "Encountered two non-identical variables with same name and data type:\n"
                            f"    {var.name_and_type()}\n"
                            "and\n"
                            f"    {live_var.name_and_type()}\n"
                        )
                    elif deconstify(var.dtype) == deconstify(live_var.dtype):
                        #   Same type, just different constness
                        #   One of them must be non-const -> keep the non-const one
                        if live_var.dtype.const and not var.dtype.const:
                            self._live_variables[var.name] = var
                    else:
                        raise SfgException(
                            "Encountered two variables with same name but different data types:\n"
                            f"    {var.name_and_type()}\n"
                            "and\n"
                            f"    {live_var.name_and_type()}"
                        )
            else:
                self._live_variables[var.name] = var


@dataclass(frozen=True)
class PostProcessingResult:
    function_params: set[SfgVar]


class CallTreePostProcessing:
    def __call__(self, ast: SfgCallTreeNode) -> PostProcessingResult:
        live_vars = self.get_live_variables(ast)
        return PostProcessingResult(live_vars)

    def handle_sequence(self, seq: SfgSequence, ppc: PostProcessingContext):
        def iter_nested_sequences(seq: SfgSequence):
            for i in range(len(seq.children) - 1, -1, -1):
                c = seq.children[i]

                if isinstance(c, SfgDeferredNode):
                    c = c.expand(ppc)
                    seq[i] = c

                if isinstance(c, SfgSequence):
                    iter_nested_sequences(c)
                else:
                    if isinstance(c, SfgStatements):
                        ppc._define(c.defines, c.code_string)

                    ppc._use(self.get_live_variables(c))

        iter_nested_sequences(seq)

    def get_live_variables(self, node: SfgCallTreeNode) -> set[SfgVar]:
        match node:
            case SfgSequence():
                ppc = PostProcessingContext()
                self.handle_sequence(node, ppc)
                return ppc.live_variables

            case SfgDeferredNode():
                raise SfgException("Deferred nodes can only occur inside a sequence.")

            case _:
                return node.depends.union(
                    *(self.get_live_variables(c) for c in node.children)
                )


class SfgDeferredNode(SfgCallTreeNode, ABC):
    """Nodes of this type are inserted as placeholders into the kernel call tree
    and need to be expanded at a later time.

    Subclasses of SfgDeferredNode correspond to nodes that cannot be created yet
    because information required for their construction is not yet known.
    """

    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        raise SfgException(
            "Invalid access into deferred node; deferred nodes must be expanded first."
        )

    @abstractmethod
    def expand(self, ppc: PostProcessingContext) -> SfgCallTreeNode:
        pass

    def get_code(self, cstyle: CodeStyle) -> str:
        raise SfgException(
            "Invalid access into deferred node; deferred nodes must be expanded first."
        )


class SfgDeferredParamSetter(SfgDeferredNode):
    def __init__(self, param: SfgVar | sp.Symbol, rhs: ExprLike):
        self._lhs = param
        self._rhs = rhs

    def expand(self, ppc: PostProcessingContext) -> SfgCallTreeNode:
        live_var = ppc.get_live_variable(self._lhs.name)
        if live_var is not None:
            code = f"{live_var.dtype.c_string()} {live_var.name} = {self._rhs};"
            return SfgStatements(
                code, (live_var,), depends(self._rhs), includes(self._rhs)
            )
        else:
            return SfgSequence([])


class SfgDeferredFieldMapping(SfgDeferredNode):
    """Deferred mapping of a pystencils field to a field data structure."""

    #   NOTE ON Scalar Fields
    #
    #   pystencils permits explicit (`index_shape = (1,)`) and implicit (`index_shape = ()`)
    #   scalar fields. In order to handle both equivalently,
    #   we ignore the trivial explicit scalar dimension in field extraction.
    #   This makes sure that explicit D-dimensional scalar fields
    #   can be mapped onto D-dimensional data structures, and do not require that
    #   D+1st dimension.

    def __init__(
        self,
        psfield: Field,
        extraction: SupportsFieldExtraction,
        cast_indexing_symbols: bool = True,
    ):
        self._field = psfield
        self._extraction = extraction
        self._cast_indexing_symbols = cast_indexing_symbols

    def expand(self, ppc: PostProcessingContext) -> SfgCallTreeNode:
        #    Find field pointer
        ptr: SfgKernelParamVar | None = None
        rank: int

        if self._field.index_shape == (1,):
            #   explicit scalar field -> ignore index dimensions
            rank = self._field.spatial_dimensions
        else:
            rank = len(self._field.shape)

        shape: list[SfgKernelParamVar | str | None] = [None] * rank
        strides: list[SfgKernelParamVar | str | None] = [None] * rank

        for param in ppc.live_variables:
            if isinstance(param, SfgKernelParamVar):
                for prop in param.wrapped.properties:
                    match prop:
                        case FieldBasePtr(field) if field == self._field:
                            ptr = param
                        case FieldShape(field, coord) if field == self._field:  # type: ignore
                            shape[coord] = param  # type: ignore
                        case FieldStride(field, coord) if field == self._field:  # type: ignore
                            strides[coord] = param  # type: ignore

        #   Find constant or otherwise determined sizes
        for coord, s in enumerate(self._field.shape[:rank]):
            if shape[coord] is None:
                shape[coord] = str(s)

        #   Find constant or otherwise determined strides
        for coord, s in enumerate(self._field.strides[:rank]):
            if strides[coord] is None:
                strides[coord] = str(s)

        #   Now we have all the symbols, start extracting them
        nodes = []
        done: set[SfgKernelParamVar] = set()

        if ptr is not None:
            expr = self._extraction._extract_ptr()
            nodes.append(
                SfgStatements(
                    f"{ptr.dtype.c_string()} {ptr.name} {{ {expr} }};",
                    (ptr,),
                    depends(expr),
                    includes(expr),
                )
            )

        def maybe_cast(expr: AugExpr, target_type: PsType) -> AugExpr:
            if self._cast_indexing_symbols:
                return AugExpr(target_type).bind(
                    "{}( {} )", deconstify(target_type).c_string(), expr
                )
            else:
                return expr

        def get_shape(coord, symb: SfgKernelParamVar | str):
            expr = self._extraction._extract_size(coord)

            if expr is None:
                raise SfgException(
                    f"Cannot extract shape in coordinate {coord} from {self._extraction}"
                )

            if isinstance(symb, SfgKernelParamVar) and symb not in done:
                done.add(symb)
                expr = maybe_cast(expr, symb.dtype)
                return SfgStatements(
                    f"{symb.dtype.c_string()} {symb.name} {{ {expr} }};",
                    (symb,),
                    depends(expr),
                    includes(expr),
                )
            else:
                return SfgStatements(f"/* {expr} == {symb} */", (), ())

        def get_stride(coord, symb: SfgKernelParamVar | str):
            expr = self._extraction._extract_stride(coord)

            if expr is None:
                raise SfgException(
                    f"Cannot extract stride in coordinate {coord} from {self._extraction}"
                )

            if isinstance(symb, SfgKernelParamVar) and symb not in done:
                done.add(symb)
                expr = maybe_cast(expr, symb.dtype)
                return SfgStatements(
                    f"{symb.dtype.c_string()} {symb.name} {{ {expr} }};",
                    (symb,),
                    depends(expr),
                    includes(expr),
                )
            else:
                return SfgStatements(f"/* {expr} == {symb} */", (), ())

        nodes += [get_shape(c, s) for c, s in enumerate(shape) if s is not None]
        nodes += [get_stride(c, s) for c, s in enumerate(strides) if s is not None]

        return SfgSequence(nodes)


class SfgDeferredVectorMapping(SfgDeferredNode):
    def __init__(
        self,
        scalars: Sequence[sp.Symbol | SfgVar],
        vector: SupportsVectorExtraction,
    ):
        self._scalars = {sc.name: (i, sc) for i, sc in enumerate(scalars)}
        self._vector = vector

    def expand(self, ppc: PostProcessingContext) -> SfgCallTreeNode:
        nodes = []

        for param in ppc.live_variables:
            if param.name in self._scalars:
                idx, _ = self._scalars[param.name]
                expr = self._vector._extract_component(idx)
                nodes.append(
                    SfgStatements(
                        f"{param.dtype.c_string()} {param.name} {{ {expr} }};",
                        (param,),
                        depends(expr),
                        includes(expr),
                    )
                )

        return SfgSequence(nodes)
