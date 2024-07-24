from pystencils.field import Field
from pystencils.types import PsType, PsCustomType

from ...lang import SrcField, SrcVector, AugExpr, IFieldExtraction
from ...ir.source_components import SfgHeaderInclude


class StdVector(SrcVector, SrcField):
    def __init__(
        self,
        T: PsType,
        unsafe: bool = False,
        reference: bool = True,
    ):
        typestring = f"std::vector< {(T.c_string())} > {'&' if reference else ''}"
        super(StdVector, self).__init__(PsCustomType(typestring))

        self._element_type = T
        self._unsafe = unsafe

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return {
            SfgHeaderInclude("vector", system_header=True),
        }

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


def std_vector_ref(field: Field):
    return StdVector(field.dtype, unsafe=False, reference=True).var(field.name)
