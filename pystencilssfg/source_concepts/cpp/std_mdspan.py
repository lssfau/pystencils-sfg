from typing import Set, Union, Tuple

from pystencils.typing import FieldPointerSymbol, FieldStrideSymbol, FieldShapeSymbol

from ...tree import SfgStatements
from ..source_objects import SrcField
from ...source_components.header_include import SfgHeaderInclude
from ...types import PsType, cpp_typename
from ...exceptions import SfgException

class std_mdspan(SrcField):
    dynamic_extent = "std::dynamic_extent"

    def __init__(self, identifer: str, T: PsType, extents: Tuple[int, str], extents_type: PsType = int, reference: bool = False):
        T = cpp_typename(T)
        extents_type = cpp_typename(extents_type)

        typestring = f"std::mdspan< {T}, std::extents< {extents_type}, {', '.join(str(e) for e in extents)} > > {'&' if reference else ''}"
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
        dim = len(self._extents)
        if coordinate >= dim:
            if isinstance(size, FieldShapeSymbol):
                raise SfgException(f"Cannot extract size in coordinate {coordinate} from a {dim}-dimensional mdspan!")
            elif size != 1:
                raise SfgException(f"Cannot map field with size {size} in coordinate {coordinate} to {dim}-dimensional mdspan!")
            else:
                #   trivial trailing index dimensions are OK -> do nothing
                return SfgStatements(f"// {self._identifier}.extents().extent({coordinate}) == 1", (), ())

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
            raise SfgException(f"Cannot extract stride in coordinate {coordinate} from a {len(self._extents)}-dimensional mdspan")
        
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
