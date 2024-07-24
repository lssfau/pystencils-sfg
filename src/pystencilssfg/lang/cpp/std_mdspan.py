from typing import cast
from sympy import Symbol

from pystencils import Field
from pystencils.types import (
    PsType,
    PsCustomType,
    PsSignedIntegerType,
    PsUnsignedIntegerType,
)

from pystencilssfg.lang.expressions import AugExpr

from ...lang import SrcField, IFieldExtraction
from ...ir.source_components import SfgHeaderInclude


class StdMdspan(SrcField):
    dynamic_extent = "std::dynamic_extent"

    def __init__(
        self,
        T: PsType,
        extents: tuple[int | str, ...],
        extents_type: PsType = PsSignedIntegerType(64),
        reference: bool = False,
    ):
        cpp_typestr = T.c_string()
        extents_type_str = extents_type.c_string()

        extents_str = (
            f"std::extents< {extents_type_str}, {', '.join(str(e) for e in extents)} >"
        )
        typestring = (
            f"std::mdspan< {cpp_typestr}, {extents_str} > {'&' if reference else ''}"
        )
        super().__init__(PsCustomType(typestring))

        self._extents = extents
        self._dim = len(extents)

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return {SfgHeaderInclude("experimental/mdspan", system_header=True)}

    def get_extraction(self) -> IFieldExtraction:
        mdspan = self

        class Extraction(IFieldExtraction):
            def ptr(self) -> AugExpr:
                return AugExpr.format("{}.data_handle()", mdspan)

            def size(self, coordinate: int) -> AugExpr | None:
                if coordinate > mdspan._dim:
                    return None
                else:
                    return AugExpr.format("{}.extents().extent({})", mdspan, coordinate)

            def stride(self, coordinate: int) -> AugExpr | None:
                if coordinate > mdspan._dim:
                    return None
                else:
                    return AugExpr.format("{}.stride({})", mdspan, coordinate)

        return Extraction()


def mdspan_ref(field: Field, extents_type: PsType = PsUnsignedIntegerType(64)):
    """Creates a `std::mdspan &` for a given pystencils field."""
    from pystencils.field import layout_string_to_tuple

    if field.layout != layout_string_to_tuple("soa", field.spatial_dimensions):
        raise NotImplementedError(
            "mdspan mapping is currently only available for structure-of-arrays fields"
        )

    extents: list[str | int] = []

    for s in field.spatial_shape:
        extents.append(
            StdMdspan.dynamic_extent if isinstance(s, Symbol) else cast(int, s)
        )

    for s in field.index_shape:
        extents.append(StdMdspan.dynamic_extent if isinstance(s, Symbol) else s)

    return StdMdspan(
        field.dtype,
        tuple(extents),
        extents_type=extents_type,
        reference=True,
    ).var(field.name)
