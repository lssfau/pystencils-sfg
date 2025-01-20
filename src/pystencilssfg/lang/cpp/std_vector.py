from pystencils.field import Field
from pystencils.types import UserTypeSpec, create_type, PsType

from ...lang import SrcField, SrcVector, AugExpr, IFieldExtraction, cpptype


class StdVector(SrcVector, SrcField):
    _template = cpptype("std::vector< {T} >", "<vector>")

    def __init__(
        self,
        T: UserTypeSpec,
        unsafe: bool = False,
        ref: bool = False,
        const: bool = False,
    ):
        T = create_type(T)
        dtype = self._template(T=T, const=const, ref=ref)
        super().__init__(dtype)

        self._element_type = T
        self._unsafe = unsafe

    @property
    def element_type(self) -> PsType:
        return self._element_type

    def get_extraction(self) -> IFieldExtraction:
        vec = self

        class Extraction(IFieldExtraction):
            def ptr(self) -> AugExpr:
                return AugExpr.format("{}.data()", vec)

            def size(self, coordinate: int) -> AugExpr | None:
                if coordinate > 0:
                    return None
                else:
                    return AugExpr.format("{}.size()", vec)

            def stride(self, coordinate: int) -> AugExpr | None:
                if coordinate > 0:
                    return None
                else:
                    return AugExpr.format("1")

        return Extraction()

    def extract_component(self, coordinate: int) -> AugExpr:
        if self._unsafe:
            return AugExpr.format("{}[{}]", self, coordinate)
        else:
            return AugExpr.format("{}.at({})", self, coordinate)

    @staticmethod
    def from_field(field: Field, ref: bool = True, const: bool = False):
        if field.spatial_dimensions > 1 or field.index_shape not in ((), (1,)):
            raise ValueError(
                f"Cannot create std::vector from more-than-one-dimensional field {field}."
            )

        return StdVector(field.dtype, unsafe=False, ref=ref, const=const).var(field.name)


def std_vector_ref(field: Field):
    from warnings import warn

    warn(
        "`std_vector_ref` is deprecated and will be removed in version 0.1. Use `std.vector.from_field` instead.",
        FutureWarning,
    )
    return StdVector.from_field(field, ref=True)
