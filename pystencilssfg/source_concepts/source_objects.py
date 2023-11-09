from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union, Set, TypeAlias, NewType

if TYPE_CHECKING:
    from ..source_components import SfgHeaderInclude
    from ..tree import SfgStatements, SfgSequence

from numpy import dtype

from abc import ABC, abstractmethod

from pystencils import TypedSymbol, Field
from pystencils.typing import AbstractType, FieldPointerSymbol, FieldStrideSymbol, FieldShapeSymbol

PsType: TypeAlias = Union[type, dtype, AbstractType]
"""Types used in interacting with pystencils.

PsType represents various ways of specifying types within pystencils.
In particular, it encompasses most ways to construct an instance of `AbstractType`,
for example via `create_type`.

(Note that, while `create_type` does accept strings, they are excluded here for
reasons of safety. It is discouraged to use strings for type specifications when working
with pystencils!)
"""

SrcType = NewType('SrcType', str)
"""Nonprimitive C/C++-Types occuring during source file generation.

Nonprimitive C/C++ types are represented by their names.
When necessary, the SFG package checks equality of types by these name strings; it does
not care about typedefs, aliases, namespaces, etc!
"""


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
    def required_includes(self) -> Set[SfgHeaderInclude]:
        return set()
    
    def __hash__(self) -> int:
        return hash((self._identifier, self._src_type))
    
    def __eq__(self, other: SrcObject) -> bool:
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

        from ..tree import make_sequence

        return make_sequence(
            self.extract_ptr(ptr),
            *(self.extract_size(c, s) for c, s in enumerate(field.shape)),
            *(self.extract_stride(c, s) for c, s in enumerate(field.strides))
        )


class SrcVector(SrcObject):
    @abstractmethod
    def extract_component(self, destination: TypedSymbolOrObject, coordinate: int):
        pass
