from pystencils import Field, DynamicType
from pystencils.types import UserTypeSpec, create_type, PsType

from ...lang import SupportsFieldExtraction, AugExpr, cpptype


class StdSpan(AugExpr, SupportsFieldExtraction):
    _template = cpptype("std::span< {T} >", "<span>")

    def __init__(self, T: UserTypeSpec, ref=False, const=False):
        T = create_type(T)
        dtype = self._template(T=T, const=const, ref=ref)
        self._element_type = T
        super().__init__(dtype)

    @property
    def element_type(self) -> PsType:
        return self._element_type

    def _extract_ptr(self) -> AugExpr:
        return AugExpr.format("{}.data()", self)

    def _extract_size(self, coordinate: int) -> AugExpr | None:
        if coordinate > 0:
            return None
        else:
            return AugExpr.format("{}.size()", self)

    def _extract_stride(self, coordinate: int) -> AugExpr | None:
        if coordinate > 0:
            return None
        else:
            return AugExpr.format("1")

    @staticmethod
    def from_field(field: Field, ref: bool = False, const: bool = False):
        if field.spatial_dimensions > 1 or field.index_shape not in ((), (1,)):
            raise ValueError(
                "Only one-dimensional fields with trivial index dimensions can be mapped onto `std::span`"
            )
        if isinstance(field.dtype, DynamicType):
            raise ValueError("Cannot map dynamically typed field to std::span")

        return StdSpan(field.dtype, ref=ref, const=const).var(field.name)


def std_span_ref(field: Field):
    from warnings import warn

    warn(
        "`std_span_ref` is deprecated and will be removed in version 0.1. Use `std.span.from_field` instead.",
        FutureWarning,
    )
    return StdSpan.from_field(field, ref=True)
