from typing import Sequence

from pystencils.types import PsType, PsCustomType
from pystencils.backend.kernelfunction import KernelParameter

from ...lang import SrcVector, AugExpr
from ...ir.source_components import SfgHeaderInclude


class StdTuple(SrcVector):
    def __init__(
        self,
        element_types: Sequence[PsType],
        const: bool = False,
        ref: bool = False,
    ):
        self._element_types = element_types
        self._length = len(element_types)
        elt_type_strings = tuple(t.c_string() for t in self._element_types)
        tuple_type = f"{'const' if const else ''} std::tuple< {', '.join(elt_type_strings)} > {'&' if ref else ''}"
        super().__init__(PsCustomType(tuple_type))

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return {SfgHeaderInclude("tuple", system_header=True)}

    def extract_component(self, coordinate: int) -> AugExpr:
        if coordinate < 0 or coordinate >= self._length:
            raise ValueError(
                f"Index {coordinate} out-of-bounds for std::tuple with {self._length} entries."
            )

        return AugExpr.format("std::get< {} >({})", coordinate, self)


def std_tuple_ref(
    identifier: str, components: Sequence[KernelParameter], const: bool = True
):
    elt_types = tuple(c.dtype for c in components)
    return StdTuple(elt_types, const=const, ref=True).var(identifier)
