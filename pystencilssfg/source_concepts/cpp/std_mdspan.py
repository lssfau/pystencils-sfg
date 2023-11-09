from typing import Union

from pystencils.typing import FieldPointerSymbol, FieldStrideSymbol, FieldShapeSymbol

from ...tree import SfgStatements
from ..containers import SrcField

class std_mdspan(SrcField):
    def __init__(self, identifer: str):
        super().__init__("std::mdspan", identifer)

    def extract_ptr(self, ptr_symbol: FieldPointerSymbol):
        return SfgStatements(
            f"{ptr_symbol.dtype} {ptr_symbol.name} = {self._identifier}.data_handle();",
            (ptr_symbol, ),
            (self, )
        )

    def extract_size(self, coordinate: int, size: Union[int, FieldShapeSymbol]) -> SfgStatements:
        if isinstance(size, FieldShapeSymbol):
            return SfgStatements(
                    f"{size.dtype} {size.name} = {self._identifier}.extents().extent({coordinate});",
                    (size, ),
                    (self, )
                )
        else:
            return SfgStatements(
                f"assert( {self._identifier}.extents().extent({coordinate}) == {size} );",
                (), (self, )
            )
        
    def extract_stride(self, coordinate: int, stride: Union[int, FieldShapeSymbol]) -> SfgStatements:
        if isinstance(stride, FieldShapeSymbol):
            return SfgStatements(
                    f"{stride.dtype} {stride.name} = {self._identifier}.stride({coordinate});",
                    (stride, ),
                    (self, )
                )
        else:
            return SfgStatements(
                f"assert( {self._identifier}.stride({coordinate}) == {stride} );",
                (), (self, )
            )
