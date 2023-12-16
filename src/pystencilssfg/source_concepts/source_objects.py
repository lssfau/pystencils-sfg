from __future__ import annotations

from typing import TYPE_CHECKING, Union, TypeAlias

from abc import ABC, abstractmethod

from pystencils import TypedSymbol, Field
from pystencils.typing import FieldPointerSymbol, FieldStrideSymbol, FieldShapeSymbol

from ..types import SrcType

if TYPE_CHECKING:
    from ..source_components import SfgHeaderInclude
    from ..tree import SfgStatements, SfgSequence


class SrcObject:
    """C/C++ object of nonprimitive type.

    Two objects are identical if they have the same identifier and type string."""

    def __init__(self, identifier: str, src_type: SrcType):
        self._identifier = identifier
        self._src_type = src_type

    @property
    def identifier(self):
        return self._identifier

    @property
    def name(self) -> str:
        """For interface compatibility with ps.TypedSymbol"""
        return self._identifier

    @property
    def dtype(self):
        return self._src_type

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return set()

    def __hash__(self) -> int:
        return hash((self._identifier, self._src_type))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SrcObject)
            and self._identifier == other._identifier
            and self._src_type == other._src_type
        )

    def __str__(self) -> str:
        return self.name


TypedSymbolOrObject: TypeAlias = TypedSymbol | SrcObject


class SrcField(SrcObject, ABC):
    """Represents a C++ data structure that can be mapped to a *pystencils* field.

    Subclasses of `SrcField` are meant to be used in [SfgComposer.map_field][pystencilssfg.SfgComposer.map_field]
    to produce the necessary mapping code from a high-level C++ field data structure to a pystencils field.

    Subclasses of `SrcField` must implement `extract_ptr`, `extract_size` and `extract_stride`
    to emit code extracting field pointers and indexing information from the high-level concept.

    Currently, *pystencils-sfg* provides an implementation for the C++ `std::vector` and `std::mdspan` classes via
    [StdVector][pystencilssfg.source_concepts.cpp.StdVector] and
    [StdMdspan][pystencilssfg.source_concepts.cpp.StdMdspan].
    """

    def __init__(self, identifier: str, src_type: SrcType):
        super().__init__(identifier, src_type)

    @abstractmethod
    def extract_ptr(self, ptr_symbol: FieldPointerSymbol) -> SfgStatements:
        pass

    @abstractmethod
    def extract_size(
        self, coordinate: int, size: Union[int, FieldShapeSymbol]
    ) -> SfgStatements:
        pass

    @abstractmethod
    def extract_stride(
        self, coordinate: int, stride: Union[int, FieldStrideSymbol]
    ) -> SfgStatements:
        pass

    def extract_parameters(self, field: Field) -> SfgSequence:
        ptr = FieldPointerSymbol(field.name, field.dtype, False)

        from ..composer import make_sequence

        return make_sequence(
            self.extract_ptr(ptr),
            *(self.extract_size(c, s) for c, s in enumerate(field.shape)),
            *(self.extract_stride(c, s) for c, s in enumerate(field.strides)),
        )


class SrcVector(SrcObject, ABC):
    """Represents a C++ abstraction of a mathematical vector that can be mapped to a vector of symbols.

    Subclasses of `SrcVector` are meant to be used in [SfgComposer.map_vector][pystencilssfg.SfgComposer.map_vector]
    to produce the necessary mapping code from a high-level C++ vector data structure to a vector of symbols.

    Subclasses of `SrcVector` must implement `extract_component` to emit code extracting scalar values
    from the high-level vector.

    Currently, *pystencils-sfg* provides an implementation for the C++ `std::vector` via
    [StdVector][pystencilssfg.source_concepts.cpp.StdVector].
    """

    @abstractmethod
    def extract_component(
        self, destination: TypedSymbolOrObject, coordinate: int
    ) -> SfgStatements:
        pass
