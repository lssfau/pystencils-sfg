from typing import Optional, Union
from abc import ABC, abstractmethod

from pystencils import Field
from pystencils.typing import FieldPointerSymbol, FieldStrideSymbol, FieldShapeSymbol

from .source_concepts import SrcObject
from ..tree import SfgStatements, SfgSequence

class SrcField(SrcObject):
    def __init__(self, src_type, identifier: Optional[str]):
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

