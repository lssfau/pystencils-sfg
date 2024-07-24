from typing import Union

from pystencils.field import Field
from pystencils.types import PsType, PsCustomType

from ...lang import SrcField, IFieldExtraction, AugExpr
from ...ir.source_components import SfgHeaderInclude
from ...exceptions import SfgException


class StdSpan(SrcField):
    def __init__(self, T: Union[PsCustomType, PsType], ref=True, const=False):
        src_type = f"{'const ' if const else ''}std::span< {T.c_string()} > {'&' if ref else ''}"
        self._element_type = T
        super().__init__(PsCustomType(src_type))

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return {
            SfgHeaderInclude("span", system_header=True),
        }

    def get_extraction(self) -> IFieldExtraction:
        span = self

        class Extraction(IFieldExtraction):
            def ptr(self) -> AugExpr:
                return AugExpr.format("{}.data()", span)

            def size(self, coordinate: int) -> AugExpr | None:
                if coordinate > 0:
                    return None
                else:
                    return AugExpr.format("{}.size()", span)

            def stride(self, coordinate: int) -> AugExpr | None:
                if coordinate > 0:
                    return None
                else:
                    return AugExpr.format("1")

        return Extraction()


def std_span_ref(field: Field):
    if field.spatial_dimensions > 1 or field.index_shape not in ((), (1,)):
        raise SfgException(
            "Only one-dimensional fields with trivial index dimensions can be mapped onto `std::span`"
        )
    return StdSpan(field.dtype, True, False).var(field.name)
