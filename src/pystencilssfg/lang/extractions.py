from __future__ import annotations
from typing import Protocol, runtime_checkable
from abc import abstractmethod

from .expressions import AugExpr


@runtime_checkable
class SupportsFieldExtraction(Protocol):
    """Protocol for field pointer and indexing extraction.

    Objects adhering to this protocol are understood to provide expressions
    for the base pointer, shape, and stride properties of a field.
    They can therefore be passed to `sfg.map_field <SfgBasicComposer.map_field>`.
    """

    #  how-to-guide begin
    @abstractmethod
    def _extract_ptr(self) -> AugExpr:
        """Extract the field base pointer.

        Return an expression which represents the base pointer
        of this field data structure.

        :meta public:
        """

    @abstractmethod
    def _extract_size(self, coordinate: int) -> AugExpr | None:
        """Extract field size in a given coordinate.

        If ``coordinate`` is valid for this field (i.e. smaller than its dimensionality),
        return an expression representing the logical size of this field
        in the given dimension.
        Otherwise, return `None`.

        :meta public:
        """

    @abstractmethod
    def _extract_stride(self, coordinate: int) -> AugExpr | None:
        """Extract field stride in a given coordinate.

        If ``coordinate`` is valid for this field (i.e. smaller than its dimensionality),
        return an expression representing the memory linearization stride of this field
        in the given dimension.
        Otherwise, return `None`.

        :meta public:
        """


#  how-to-guide end


@runtime_checkable
class SupportsVectorExtraction(Protocol):
    """Protocol for component extraction from a vector.

    Objects adhering to this protocol are understood to provide
    access to the entries of a vector
    and can therefore be passed to `sfg.map_vector <SfgBasicComposer.map_vector>`.
    """

    @abstractmethod
    def _extract_component(self, coordinate: int) -> AugExpr: ...
