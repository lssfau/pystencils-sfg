from typing import Union, cast

import numpy as np

from pystencils import Field
from pystencils.typing import FieldPointerSymbol, FieldStrideSymbol, FieldShapeSymbol

from ...tree import SfgStatements
from ..source_objects import SrcField
from ...source_components import SfgHeaderInclude
from ...types import PsType, cpp_typename, SrcType
from ...exceptions import SfgException


class StdMdspan(SrcField):
    dynamic_extent = "std::dynamic_extent"

    def __init__(self, identifer: str,
                 T: PsType,
                 extents: tuple[int | str, ...],
                 extents_type: PsType = int,
                 reference: bool = False):
        cpp_typestr = cpp_typename(T)
        extents_type_str = cpp_typename(extents_type)

        extents_str = f"std::extents< {extents_type_str}, {', '.join(str(e) for e in extents)} >"
        typestring = f"std::mdspan< {cpp_typestr}, {extents_str} > {'&' if reference else ''}"
        super().__init__(SrcType(typestring), identifer)

        self._extents = extents

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return {SfgHeaderInclude("experimental/mdspan", system_header=True)}

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
                raise SfgException(
                    f"Cannot map field with size {size} in coordinate {coordinate} to {dim}-dimensional mdspan!")
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
            raise SfgException(
                f"Cannot extract stride in coordinate {coordinate} from a {len(self._extents)}-dimensional mdspan")

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


def mdspan_ref(field: Field, extents_type: type = np.uint32):
    """Creates a `std::mdspan &` for a given pystencils field."""
    from pystencils.field import layout_string_to_tuple

    if field.layout != layout_string_to_tuple("soa", field.spatial_dimensions):
        raise NotImplementedError("mdspan mapping is currently only available for structure-of-arrays fields")

    extents: list[str | int] = []

    for s in field.spatial_shape:
        extents.append(StdMdspan.dynamic_extent if isinstance(s, FieldShapeSymbol) else cast(int, s))

    if field.index_shape != (1,):
        for s in field.index_shape:
            extents += StdMdspan.dynamic_extent if isinstance(s, FieldShapeSymbol) else s

    return StdMdspan(field.name, field.dtype,
                     tuple(extents),
                     extents_type=extents_type,
                     reference=True)
