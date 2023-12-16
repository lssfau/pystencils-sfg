from typing import Sequence

from pystencils.typing import BasicType, TypedSymbol

from ...tree import SfgStatements
from ..source_objects import SrcVector
from ..source_objects import TypedSymbolOrObject
from ...types import SrcType, cpp_typename
from ...source_components import SfgHeaderInclude


class StdTuple(SrcVector):
    def __init__(
        self,
        identifier: str,
        element_types: Sequence[BasicType],
        const: bool = False,
        ref: bool = False,
    ):
        self._element_types = element_types
        self._length = len(element_types)
        elt_type_strings = tuple(cpp_typename(t) for t in self._element_types)
        src_type = f"{'const' if const else ''} std::tuple< {', '.join(elt_type_strings)} > {'&' if ref else ''}"
        super().__init__(identifier, SrcType(src_type))

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return {SfgHeaderInclude("tuple", system_header=True)}

    def extract_component(self, destination: TypedSymbolOrObject, coordinate: int):
        if coordinate < 0 or coordinate >= self._length:
            raise ValueError(
                f"Index {coordinate} out-of-bounds for std::tuple with {self._length} entries."
            )

        if destination.dtype != self._element_types[coordinate]:
            raise ValueError(
                f"Cannot extract type {destination.dtype} from std::tuple entry "
                "of type {self._element_types[coordinate]}"
            )

        return SfgStatements(
            f"{destination.dtype} {destination.name} = std::get< {coordinate} >({self.identifier});",
            (destination,),
            (self,),
        )


def std_tuple_ref(
    identifier: str, components: Sequence[TypedSymbol], const: bool = True
):
    elt_types = tuple(c.dtype for c in components)
    return StdTuple(identifier, elt_types, const=const, ref=True)
