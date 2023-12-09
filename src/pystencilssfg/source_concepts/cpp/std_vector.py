from typing import Union

from pystencils.field import Field, FieldType
from pystencils.typing import FieldPointerSymbol, FieldStrideSymbol, FieldShapeSymbol

from ...tree import SfgStatements
from ..source_objects import SrcField, SrcVector
from ..source_objects import TypedSymbolOrObject
from ...types import SrcType, PsType, cpp_typename
from ...source_components import SfgHeaderInclude, SfgClass
from ...exceptions import SfgException


class StdVector(SrcVector, SrcField):
    def __init__(
        self,
        identifer: str,
        T: Union[SrcType, PsType],
        unsafe: bool = False,
        reference: bool = True,
    ):
        typestring = f"std::vector< {cpp_typename(T)} > {'&' if reference else ''}"
        super(StdVector, self).__init__(identifer, SrcType(typestring))

        self._element_type = T
        self._unsafe = unsafe

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return {
            SfgHeaderInclude("cassert", system_header=True),
            SfgHeaderInclude("vector", system_header=True),
        }

    def extract_ptr(self, ptr_symbol: FieldPointerSymbol):
        if ptr_symbol.dtype != self._element_type:
            if self._unsafe:
                mapping = f"{ptr_symbol.dtype} {ptr_symbol.name} = ({ptr_symbol.dtype}) {self._identifier}.data();"
            else:
                raise SfgException(
                    "Field type and std::vector element type do not match, and unsafe extraction was not enabled."
                )
        else:
            mapping = (
                f"{ptr_symbol.dtype} {ptr_symbol.name} = {self._identifier}.data();"
            )

        return SfgStatements(mapping, (ptr_symbol,), (self,))

    def extract_size(
        self, coordinate: int, size: Union[int, FieldShapeSymbol]
    ) -> SfgStatements:
        if coordinate > 0:
            if isinstance(size, FieldShapeSymbol):
                raise SfgException(
                    f"Cannot extract size in coordinate {coordinate} from std::vector!"
                )
            elif size != 1:
                raise SfgException(
                    f"Cannot map field with size {size} in coordinate {coordinate} to std::vector!"
                )
            else:
                #   trivial trailing index dimensions are OK -> do nothing
                return SfgStatements(
                    f"// {self._identifier}.size({coordinate}) == 1", (), ()
                )

        if isinstance(size, FieldShapeSymbol):
            return SfgStatements(
                f"{size.dtype} {size.name} = ({size.dtype}) {self._identifier}.size();",
                (size,),
                (self,),
            )
        else:
            return SfgStatements(
                f"assert( {self._identifier}.size() == {size} );", (), (self,)
            )

    def extract_stride(
        self, coordinate: int, stride: Union[int, FieldStrideSymbol]
    ) -> SfgStatements:
        if coordinate == 1:
            if stride != 1:
                raise SfgException(
                    "Can only map fields with trivial index stride onto std::vector!"
                )

        if coordinate > 1:
            raise SfgException(
                f"Cannot extract stride in coordinate {coordinate} from std::vector"
            )

        if isinstance(stride, FieldStrideSymbol):
            return SfgStatements(f"{stride.dtype} {stride.name} = 1;", (stride,), ())
        elif stride != 1:
            raise SfgException(
                "Can only map fields with trivial strides onto std::vector!"
            )
        else:
            return SfgStatements(
                f"// {self._identifier}.stride({coordinate}) == 1", (), ()
            )

    def extract_component(
        self, destination: TypedSymbolOrObject, coordinate: int
    ) -> SfgStatements:
        if self._unsafe:
            mapping = f"{destination.dtype} {destination.name} = {self._identifier}[{coordinate}];"
        else:
            mapping = f"{destination.dtype} {destination.name} = {self._identifier}.at({coordinate});"

        return SfgStatements(mapping, (destination,), (self,))


def std_vector_ref(field: Field, src_struct: SfgClass):
    if field.field_type != FieldType.INDEXED:
        raise ValueError("Can only create std::vector for index fields")

    return StdVector(field.name, src_struct.src_type, unsafe=True, reference=True)
