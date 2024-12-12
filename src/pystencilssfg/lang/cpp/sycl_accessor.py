from ...lang import SrcField, IFieldExtraction

from pystencils import Field
from pystencils.types import UserTypeSpec, create_type

from ...lang import AugExpr, cpptype, Ref


class SyclAccessor(SrcField):
    """Represent a
    `SYCL Accessor <https://registry.khronos.org/SYCL/specs/sycl-2020/html/sycl-2020.html#subsec:accessors>`_.

    .. note::

        Sycl Accessor do not expose information about strides, so the linearization is done under
        the assumption that the underlying memory is contiguous, as descibed
        `here <https://registry.khronos.org/SYCL/specs/sycl-2020/html/sycl-2020.html#_multi_dimensional_objects_and_linearization>`_
    """  # noqa: E501

    _template = cpptype("sycl::accessor< {T}, {dims} >", "<sycl/sycl.hpp>")

    def __init__(
        self,
        T: UserTypeSpec,
        dimensions: int,
        ref: bool = False,
        const: bool = False,
    ):
        T = create_type(T)
        if dimensions > 3:
            raise ValueError("sycl accessors can only have dims 1, 2 or 3")
        dtype = self._template(T=T, dims=dimensions, const=const)
        if ref:
            dtype = Ref(dtype)

        super().__init__(dtype)

        self._dim = dimensions
        self._inner_stride = 1

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

    @staticmethod
    def from_field(field: Field, ref: bool = True):
        """Creates a `sycl::accessor &` for a given pystencils field."""

        return SyclAccessor(
            field.dtype,
            field.spatial_dimensions + field.index_dimensions,
            ref=ref,
        ).var(field.name)
