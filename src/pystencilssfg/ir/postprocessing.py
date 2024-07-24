from __future__ import annotations
from typing import TYPE_CHECKING, Sequence
import warnings
from functools import reduce
from dataclasses import dataclass

from abc import ABC, abstractmethod

import sympy as sp

from pystencils import Field, TypedSymbol
from pystencils.backend.kernelfunction import (
    FieldPointerParam,
    FieldShapeParam,
    FieldStrideParam,
)

from ..exceptions import SfgException

from .call_tree import SfgCallTreeNode, SfgCallTreeLeaf, SfgSequence, SfgStatements
from ..ir.source_components import SfgVar, SfgSymbolLike
from ..lang import IFieldExtraction, SrcField, SrcVector

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
        self.live_objects: set[SfgVar] = set()

    def is_method(self) -> bool:
        return self.enclosing_class is not None

    def get_enclosing_class(self) -> SfgClass:
        if self.enclosing_class is None:
            raise SfgException("Cannot get the enclosing class of a free function.")

        return self.enclosing_class


@dataclass(frozen=True)
class PostProcessingResult:
    function_params: set[SfgVar]


class CallTreePostProcessing:
    def __init__(self, enclosing_class: SfgClass | None = None):
        self._enclosing_class = enclosing_class
        self._flattener = FlattenSequences()

    def __call__(self, ast: SfgCallTreeNode) -> PostProcessingResult:
        params = self.get_live_objects(ast)
        params_by_name: dict[str, SfgVar] = dict()

        for param in params:
            if param.name in params_by_name:
                other = params_by_name[param.name]

                if param.dtype == other.dtype:
                    warnings.warn(
                        "Encountered two non-identical parameters with same name and data type:\n"
                        f"    {repr(param)}\n"
                        "and\n"
                        f"    {repr(other)}\n"
                    )
                else:
                    raise SfgException(
                        "Encountered two parameters with same name but different data types:\n"
                        f"    {repr(param)}\n"
                        "and\n"
                        f"    {repr(other)}"
                    )
            params_by_name[param.name] = param

        return PostProcessingResult(set(params_by_name.values()))

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
                        ppc.live_objects -= c.defines

                    ppc.live_objects |= self.get_live_objects(c)

        iter_nested_sequences(seq)

    def get_live_objects(self, node: SfgCallTreeNode) -> set[SfgVar]:
        match node:
            case SfgSequence():
                ppc = self._ppc()
                self.handle_sequence(node, ppc)
                return ppc.live_objects

            case SfgCallTreeLeaf():
                return node.depends

            case SfgDeferredNode():
                raise SfgException("Deferred nodes can only occur inside a sequence.")

            case _:
                return reduce(
                    lambda x, y: x | y,
                    (self.get_live_objects(c) for c in node.children),
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


class SfgDeferredParamMapping(SfgDeferredNode):
    def __init__(self, lhs: SfgVar, rhs: set[SfgVar], mapping: str):
        self._lhs = lhs
        self._rhs = rhs
        self._mapping = mapping

    def expand(self, ppc: PostProcessingContext) -> SfgCallTreeNode:
        if self._lhs in ppc.live_objects:
            return SfgStatements(self._mapping, (self._lhs,), tuple(self._rhs))
        else:
            return SfgSequence([])


class SfgDeferredFieldMapping(SfgDeferredNode):
    def __init__(self, psfield: Field, extraction: IFieldExtraction | SrcField):
        self._field = psfield
        self._extraction: IFieldExtraction = (
            extraction
            if isinstance(extraction, IFieldExtraction)
            else extraction.get_extraction()
        )

    # type: ignore
    def expand(self, ppc: PostProcessingContext) -> SfgCallTreeNode:
        #    Find field pointer
        ptr: SfgSymbolLike[FieldPointerParam] | None = None
        shape: list[SfgSymbolLike[FieldShapeParam] | int | None] = [None] * len(
            self._field.shape
        )
        strides: list[SfgSymbolLike[FieldStrideParam] | int | None] = [None] * len(
            self._field.strides
        )

        for param in ppc.live_objects:
            #   idk why, but mypy does not understand these pattern matches
            match param:
                case SfgSymbolLike(FieldPointerParam(_, _, field)) if field == self._field:  # type: ignore
                    ptr = param
                case SfgSymbolLike(
                    FieldShapeParam(_, _, field, coord)  # type: ignore
                ) if field == self._field:  # type: ignore
                    shape[coord] = param  # type: ignore
                case SfgSymbolLike(
                    FieldStrideParam(_, _, field, coord)  # type: ignore
                ) if field == self._field:  # type: ignore
                    strides[coord] = param  # type: ignore

        #   Find constant sizes
        for coord, s in enumerate(self._field.shape):
            if not isinstance(s, TypedSymbol):
                shape[coord] = s

        #   Find constant strides
        for coord, s in enumerate(self._field.strides):
            if not isinstance(s, TypedSymbol):
                strides[coord] = s

        #   Now we have all the symbols, start extracting them
        nodes = []

        if ptr is not None:
            expr = self._extraction.ptr()
            nodes.append(
                SfgStatements(
                    f"{ptr.dtype} {ptr.name} {{ {expr} }};", (ptr,), expr.depends
                )
            )

        def get_shape(coord, symb: SfgSymbolLike | int):
            expr = self._extraction.size(coord)

            if expr is None:
                raise SfgException(
                    f"Cannot extract shape in coordinate {coord} from {self._extraction}"
                )

            if isinstance(symb, SfgSymbolLike):
                return SfgStatements(
                    f"{symb.dtype} {symb.name} {{ {expr} }};", (symb,), expr.depends
                )
            else:
                return SfgStatements(f"/* {expr} == {symb} */", (), ())

        def get_stride(coord, symb: SfgSymbolLike | int):
            expr = self._extraction.stride(coord)

            if expr is None:
                raise SfgException(
                    f"Cannot extract stride in coordinate {coord} from {self._extraction}"
                )

            if isinstance(symb, SfgSymbolLike):
                return SfgStatements(
                    f"{symb.dtype} {symb.name} {{ {expr} }};", (symb,), expr.depends
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

        for param in ppc.live_objects:
            if param.name in self._scalars:
                idx, _ = self._scalars[param.name]
                expr = self._vector.extract_component(idx)
                nodes.append(
                    SfgStatements(
                        f"{param.dtype} {param.name} {{ {expr} }};",
                        (param,),
                        expr.depends,
                    )
                )

        return SfgSequence(nodes)
