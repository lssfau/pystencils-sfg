from __future__ import annotations
from typing import TYPE_CHECKING, Sequence, Iterable
import warnings
from functools import reduce
from dataclasses import dataclass

from abc import ABC, abstractmethod

import sympy as sp

from pystencils import Field
from pystencils.types import deconstify, PsType
from pystencils.backend.properties import FieldBasePtr, FieldShape, FieldStride

from ..exceptions import SfgException

from .call_tree import SfgCallTreeNode, SfgCallTreeLeaf, SfgSequence, SfgStatements
from ..ir.source_components import SfgKernelParamVar
from ..lang import (
    SfgVar,
    IFieldExtraction,
    SrcField,
    SrcVector,
    ExprLike,
    AugExpr,
    depends,
    includes,
)

if TYPE_CHECKING:
    from ..context import SfgContext
    from .source_components import SfgClass


class FlattenSequences:
    """Flattens any nested sequences occuring in a kernel call tree."""

    def __call__(self, node: SfgCallTreeNode) -> None:
        self.visit(node)

    def visit(self, node: SfgCallTreeNode):
        match node:
            case SfgSequence():
                self.flatten(node)
            case _:
                for c in node.children:
                    self.visit(c)

    def flatten(self, sequence: SfgSequence) -> None:
        children_flattened: list[SfgCallTreeNode] = []

        def flatten(seq: SfgSequence):
            for c in seq.children:
                if isinstance(c, SfgSequence):
                    flatten(c)
                else:
                    children_flattened.append(c)

        flatten(sequence)

        for c in children_flattened:
            self.visit(c)

        sequence.children = children_flattened


class PostProcessingContext:
    def __init__(self, enclosing_class: SfgClass | None = None) -> None:
        self.enclosing_class: SfgClass | None = enclosing_class
        self._live_variables: dict[str, SfgVar] = dict()

    def is_method(self) -> bool:
        return self.enclosing_class is not None

    def get_enclosing_class(self) -> SfgClass:
        if self.enclosing_class is None:
            raise SfgException("Cannot get the enclosing class of a free function.")

        return self.enclosing_class

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
    def __init__(self, enclosing_class: SfgClass | None = None):
        self._enclosing_class = enclosing_class
        self._flattener = FlattenSequences()

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
                ppc = self._ppc()
                self.handle_sequence(node, ppc)
                return ppc.live_variables

            case SfgCallTreeLeaf():
                return node.depends

            case SfgDeferredNode():
                raise SfgException("Deferred nodes can only occur inside a sequence.")

            case _:
                return reduce(
                    lambda x, y: x | y,
                    (self.get_live_variables(c) for c in node.children),
                    set(),
                )

    def _ppc(self) -> PostProcessingContext:
        return PostProcessingContext(enclosing_class=self._enclosing_class)


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

    def get_code(self, ctx: SfgContext) -> str:
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
            return SfgStatements(code, (live_var,), depends(self._rhs), includes(self._rhs))
        else:
            return SfgSequence([])


class SfgDeferredFieldMapping(SfgDeferredNode):
    def __init__(
        self,
        psfield: Field,
        extraction: IFieldExtraction | SrcField,
        cast_indexing_symbols: bool = True,
    ):
        self._field = psfield
        self._extraction: IFieldExtraction = (
            extraction
            if isinstance(extraction, IFieldExtraction)
            else extraction.get_extraction()
        )
        self._cast_indexing_symbols = cast_indexing_symbols

    def expand(self, ppc: PostProcessingContext) -> SfgCallTreeNode:
        #    Find field pointer
        ptr: SfgKernelParamVar | None = None
        shape: list[SfgKernelParamVar | str | None] = [None] * len(self._field.shape)
        strides: list[SfgKernelParamVar | str | None] = [None] * len(
            self._field.strides
        )

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
        for coord, s in enumerate(self._field.shape):
            if shape[coord] is None:
                shape[coord] = str(s)

        #   Find constant or otherwise determined strides
        for coord, s in enumerate(self._field.strides):
            if strides[coord] is None:
                strides[coord] = str(s)

        #   Now we have all the symbols, start extracting them
        nodes = []
        done: set[SfgKernelParamVar] = set()

        if ptr is not None:
            expr = self._extraction.ptr()
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
            expr = self._extraction.size(coord)

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
            expr = self._extraction.stride(coord)

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
    def __init__(self, scalars: Sequence[sp.Symbol | SfgVar], vector: SrcVector):
        self._scalars = {sc.name: (i, sc) for i, sc in enumerate(scalars)}
        self._vector = vector

    def expand(self, ppc: PostProcessingContext) -> SfgCallTreeNode:
        nodes = []

        for param in ppc.live_variables:
            if param.name in self._scalars:
                idx, _ = self._scalars[param.name]
                expr = self._vector.extract_component(idx)
                nodes.append(
                    SfgStatements(
                        f"{param.dtype.c_string()} {param.name} {{ {expr} }};",
                        (param,),
                        depends(expr),
                        includes(expr),
                    )
                )

        return SfgSequence(nodes)
