from pystencils.types import UserTypeSpec, create_type

from ...lang import SupportsVectorExtraction, AugExpr, cpptype


class StdTuple(AugExpr, SupportsVectorExtraction):
    _template = cpptype("std::tuple< {ts} >", "<tuple>")

    def __init__(
        self,
        *element_types: UserTypeSpec,
        const: bool = False,
        ref: bool = False,
    ):
        self._element_types = tuple(create_type(t) for t in element_types)
        self._length = len(element_types)
        elt_type_strings = tuple(t.c_string() for t in self._element_types)

        dtype = self._template(ts=", ".join(elt_type_strings), const=const, ref=ref)
        super().__init__(dtype)

    def _extract_component(self, coordinate: int) -> AugExpr:
        if coordinate < 0 or coordinate >= self._length:
            raise ValueError(
                f"Index {coordinate} out-of-bounds for std::tuple with {self._length} entries."
            )

        return AugExpr.format("std::get< {} >({})", coordinate, self)
