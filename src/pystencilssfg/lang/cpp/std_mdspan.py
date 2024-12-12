from typing import cast
from sympy import Symbol

from pystencils import Field
from pystencils.types import (
    PsType,
    PsUnsignedIntegerType,
    UserTypeSpec,
    create_type,
)

from pystencilssfg.lang.expressions import AugExpr

from ...lang import SrcField, IFieldExtraction, cpptype, Ref, HeaderFile


class StdMdspan(SrcField):
    """Represents an `std::mdspan` instance.

    **On Standard Library Adoption**

    Since `std::mdspan` is not yet widely adopted
    (libc++ ships it as of LLVM 18, but GCC libstdc++ does not include it yet),
    you might have to manually include an implementation in your project
    (you can get a reference implementation [here](https://github.com/kokkos/mdspan)).
    However, when working with a non-standard mdspan implementation,
    the path to its the header and the namespace it is defined in will likely be different.

    To tell pystencils-sfg which headers to include and which namespace to use for `mdspan`,
    use `StdMdspan.configure`.
    """

    dynamic_extent = "std::dynamic_extent"

    _namespace = "std"
    _template = cpptype("std::mdspan< {T}, {extents} >", "<mdspan>")

    @classmethod
    def configure(cls, namespace: str = "std", header: str | HeaderFile = "<mdspan>"):
        """Configure the namespace and header `mdspan` is defined in."""
        cls._namespace = namespace
        cls._template = cpptype(f"{namespace}::mdspan< {{T}}, {{extents}} >", header)

    def __init__(
        self,
        T: UserTypeSpec,
        extents: tuple[int | str, ...],
        extents_type: PsType = PsUnsignedIntegerType(64),
        ref: bool = False,
        const: bool = False,
    ):
        T = create_type(T)

        extents_type_str = extents_type.c_string()
        extents_str = f"{self._namespace}::extents< {extents_type_str}, {', '.join(str(e) for e in extents)} >"

        dtype = self._template(T=T, extents=extents_str, const=const)

        if ref:
            dtype = Ref(dtype)
        super().__init__(dtype)

        self._extents = extents
        self._dim = len(extents)

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

    @staticmethod
    def from_field(
        field: Field,
        extents_type: PsType = PsUnsignedIntegerType(64),
        ref: bool = False,
        const: bool = False,
    ):
        """Creates a `std::mdspan` instance for a given pystencils field."""
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
            field.dtype, tuple(extents), extents_type=extents_type, ref=ref, const=const
        ).var(field.name)


def mdspan_ref(field: Field, extents_type: PsType = PsUnsignedIntegerType(64)):
    from warnings import warn

    warn(
        "`mdspan_ref` is deprecated and will be removed in version 0.1. Use `std.mdspan.from_field` instead.",
        FutureWarning,
    )
    return StdMdspan.from_field(field, extents_type, ref=True)
