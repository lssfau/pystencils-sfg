from typing import Set, Union, Tuple
from numpy import dtype

from pystencils.typing import FieldPointerSymbol, FieldStrideSymbol, FieldShapeSymbol

from pystencilssfg.source_components import SfgHeaderInclude

from ...tree import SfgStatements
from ..containers import SrcField
from ...source_components.header_include import SfgHeaderInclude
from ...exceptions import SfgException

class std_mdspan(SrcField):
    dynamic_extent = "std::dynamic_extent"

    def __init__(self, identifer: str, T: dtype, extents: Tuple[int, str]):
        from pystencils.typing import create_type
        T = create_type(T)
        typestring = f"std::mdspan< {T}, std::extents< int, {', '.join(str(e) for e in extents)} > >"
        super().__init__(typestring, identifer)

        self._extents = extents

    @property
    def required_includes(self) -> Set[SfgHeaderInclude]:
        return { SfgHeaderInclude("experimental/mdspan", system_header=True) }

    def extract_ptr(self, ptr_symbol: FieldPointerSymbol):
        return SfgStatements(
            f"{ptr_symbol.dtype} {ptr_symbol.name} = {self._identifier}.data_handle();",
            (ptr_symbol, ),
            (self, )
        )

    def extract_size(self, coordinate: int, size: Union[int, FieldShapeSymbol]) -> SfgStatements:
        if coordinate >= len(self._extents):
            raise SfgException(f"Cannot extract size in coordinate {coordinate} from a {len(self._extents)}-dimensional mdspan")

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
        
    def extract_stride(self, coordinate: int, stride: Union[int, FieldStrideSymbol]) -> SfgStatements:
        if coordinate >= len(self._extents):
            raise SfgException(f"Cannot extract size in coordinate {coordinate} from a {len(self._extents)}-dimensional mdspan")
        
        if isinstance(stride, FieldStrideSymbol):
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
