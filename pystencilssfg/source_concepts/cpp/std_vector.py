from typing import Set, Union, Tuple

from pystencils.typing import FieldPointerSymbol, FieldStrideSymbol, FieldShapeSymbol, create_type

from ...tree import SfgStatements
from ..source_objects import SrcField, SrcVector
from ..source_objects import SrcObject, SrcType, TypedSymbolOrObject
from ...source_components.header_include import SfgHeaderInclude
from ...exceptions import SfgException

class std_vector(SrcVector, SrcField):
    def __init__(self, identifer: str, T: SrcType, unsafe: bool = False):
        typestring = f"std::vector< {T} >"
        super(SrcObject, self).__init__(identifer, typestring)

        self._element_type = T
        self._unsafe = unsafe

    @property
    def required_includes(self) -> Set[SfgHeaderInclude]:
        return { SfgHeaderInclude("vector", system_header=True) }
    
    def extract_ptr(self, ptr_symbol: FieldPointerSymbol):
        if ptr_symbol.dtype != self._element_type:
            if self._unsafe:
                mapping = f"{ptr_symbol.dtype} {ptr_symbol.name} = ({ptr_symbol.dtype}) {self._identifier}.data();"
            else:
                raise SfgException("Field type and std::vector element type do not match, and unsafe extraction was not enabled.")
        else:
            mapping = f"{ptr_symbol.dtype} {ptr_symbol.name} = {self._identifier}.data();"

        return SfgStatements(mapping, (ptr_symbol,), (self,))
    
    def extract_size(self, coordinate: int, size: Union[int, FieldShapeSymbol]) -> SfgStatements:
        if coordinate > 0:
            raise SfgException(f"Cannot extract size in coordinate {coordinate} from std::vector")

        if isinstance(size, FieldShapeSymbol):
            return SfgStatements(
                    f"{size.dtype} {size.name} = {self._identifier}.size();",
                    (size, ),
                    (self, )
                )
        else:
            return SfgStatements(
                f"assert( {self._identifier}.size() == {size} );",
                (), (self, )
            )
        
    def extract_stride(self, coordinate: int, stride: Union[int, FieldStrideSymbol]) -> SfgStatements:
        if coordinate > 0:
            raise SfgException(f"Cannot extract stride in coordinate {coordinate} from std::vector")
        
        if isinstance(stride, FieldStrideSymbol):
            return SfgStatements(f"{stride.dtype} {stride.name} = 1;", (stride, ), ())
        else:
            return SfgStatements(f"assert( 1 == {stride} );", (), ())


    def extract_component(self, destination: TypedSymbolOrObject, coordinate: int):
        if self._unsafe:
            mapping = f"{destination.dtype} {destination.name} = {self._identifier}[{coordinate}];"
        else:
            mapping = f"{destination.dtype} {destination.name} = {self._identifier}.at({coordinate});"

        return SfgStatements(mapping, (destination,), (self,))



class std_vector_ref(std_vector):
    def __init__(self, identifer: str, T: SrcType):
        typestring = f"std::vector< {T} > &"
        super(SrcObject, self).__init__(identifer, typestring)
