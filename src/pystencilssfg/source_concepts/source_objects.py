from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union, TypeAlias

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

    def __init__(self, src_type: SrcType, identifier: Optional[str]):
        self._src_type = src_type
        self._identifier = identifier

    @property
    def identifier(self):
        return self._identifier

    @property
    def name(self):
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
        return (isinstance(other, SrcObject)
                and self._identifier == other._identifier
                and self._src_type == other._src_type)


TypedSymbolOrObject: TypeAlias = Union[TypedSymbol, SrcObject]


class SrcField(SrcObject, ABC):
    def __init__(self, src_type: SrcType, identifier: Optional[str]):
        super().__init__(src_type, identifier)

    @abstractmethod
    def extract_ptr(self, ptr_symbol: FieldPointerSymbol) -> SfgStatements:
        pass

    @abstractmethod
    def extract_size(self, coordinate: int, size: Union[int, FieldShapeSymbol]) -> SfgStatements:
        pass

    @abstractmethod
    def extract_stride(self, coordinate: int, stride: Union[int, FieldStrideSymbol]) -> SfgStatements:
        pass

    def extract_parameters(self, field: Field) -> SfgSequence:
        ptr = FieldPointerSymbol(field.name, field.dtype, False)

        from ..composer import make_sequence

        return make_sequence(
            self.extract_ptr(ptr),
            *(self.extract_size(c, s) for c, s in enumerate(field.shape)),
            *(self.extract_stride(c, s) for c, s in enumerate(field.strides))
        )


class SrcVector(SrcObject, ABC):
    @abstractmethod
    def extract_component(self, destination: TypedSymbolOrObject, coordinate: int) -> SfgStatements:
        pass
