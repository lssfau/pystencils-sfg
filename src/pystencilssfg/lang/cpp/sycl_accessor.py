from ...lang import SrcField, IFieldExtraction
from ...ir.source_components import SfgHeaderInclude

from pystencils import Field
from pystencils.types import (
    PsType,
    PsCustomType,
)

from pystencilssfg.lang.expressions import AugExpr


class SyclAccessor(SrcField):
    def __init__(
        self,
        T: PsType,
        dimensions: int,
        reference: bool = False,
    ):
        cpp_typestr = T.c_string()
        if 3 < dimensions:
            raise ValueError("sycl accessors can only have dims 1, 2 or 3")
        typestring = (
            f"sycl::accessor< {cpp_typestr}, {dimensions} > {'&' if reference else ''}"
        )
        super().__init__(PsCustomType(typestring))
        self._dim = dimensions
        self._inner_stride = 1

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return {SfgHeaderInclude("sycl/sycl.hpp", system_header=True)}

    def get_extraction(self) -> IFieldExtraction:
        accessor = self

        class Extraction(IFieldExtraction):
            def ptr(self) -> AugExpr:
                return AugExpr.format(
                    "{}.get_multi_ptr<sycl::access::decorated::no>().get()",
                    accessor,
                )

            def size(self, coordinate: int) -> AugExpr | None:
                if coordinate > accessor._dim:
                    return None
                else:
                    return AugExpr.format(
                        "{}.get_range().get({})", accessor, coordinate
                    )

            def stride(self, coordinate: int) -> AugExpr | None:
                if coordinate > accessor._dim:
                    return None
                elif coordinate == accessor._dim - 1:
                    return AugExpr.format("{}", accessor._inner_stride)
                else:
                    exprs = []
                    args = []
                    for d in range(coordinate + 1, accessor._dim):
                        args.extend([accessor, d])
                        exprs.append("{}.get_range().get({})")
                    expr = " * ".join(exprs)
                    expr += " * {}"
                    return AugExpr.format(expr, *args, accessor._inner_stride)

        return Extraction()


def sycl_accessor_ref(field: Field):
    """Creates a `sycl::accessor &` for a given pystencils field."""
    # Sycl Accessor do not expose information about strides, so the linearization is like here
    # https://registry.khronos.org/SYCL/specs/sycl-2020/html/sycl-2020.html#_multi_dimensional_objects_and_linearization

    return SyclAccessor(
        field.dtype,
        field.spatial_dimensions + field.index_dimensions,
        reference=True,
    ).var(field.name)
