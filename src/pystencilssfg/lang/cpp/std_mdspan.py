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

from ...lang import SrcField, IFieldExtraction, cpptype, Ref, HeaderFile, ExprLike


class StdMdspan(SrcField):
    """Represents an `std::mdspan` instance.

    The `std::mdspan <https://en.cppreference.com/w/cpp/container/mdspan>`_
    provides non-owning views into contiguous or strided n-dimensional arrays.
    It has been added to the C++ STL with the C++23 standard.
    As such, it is a natural data structure to target with pystencils kernels.

    **Concerning Headers and Namespaces**

    Since ``std::mdspan`` is not yet widely adopted
    (libc++ ships it as of LLVM 18, but GCC libstdc++ does not include it yet),
    you might have to manually include an implementation in your project
    (you can get a reference implementation at https://github.com/kokkos/mdspan).
    However, when working with a non-standard mdspan implementation,
    the path to its the header and the namespace it is defined in will likely be different.

    To tell pystencils-sfg which headers to include and which namespace to use for ``mdspan``,
    use `StdMdspan.configure`;
    for instance, adding this call before creating any ``mdspan`` objects will
    set their namespace to `std::experimental`, and require ``<experimental/mdspan>`` to be imported:

    >>> from pystencilssfg.lang.cpp import std
    >>> std.mdspan.configure("std::experimental", "<experimental/mdspan>")

    **Creation from pystencils fields**

    Using `from_field`, ``mdspan`` objects can be created directly from `Field <pystencils.Field>` instances.
    The `extents`_ of the ``mdspan`` type will be inferred from the field;
    each fixed entry in the field's shape will become a fixed entry of the ``mdspan``'s extents.

    The ``mdspan``'s `layout_policy`_ defaults to `std::layout_stride`_,
    which might not be the optimal choice depending on the memory layout of your fields.
    You may therefore override this by specifying the name of the desired layout policy.
    To map pystencils field layout identifiers to layout policies, consult the following table:

    +------------------------+--------------------------+
    | pystencils Layout Name | ``mdspan`` Layout Policy |
    +========================+==========================+
    | ``"fzyx"``             | `std::layout_left`_      |
    | ``"soa"``              |                          |
    | ``"f"``                |                          |
    | ``"reverse_numpy"``    |                          |
    +------------------------+--------------------------+
    | ``"c"``                | `std::layout_right`_     |
    | ``"numpy"``            |                          |
    +------------------------+--------------------------+
    | ``"zyxf"``             | `std::layout_stride`_    |
    | ``"aos"``              |                          |
    +------------------------+--------------------------+

    The array-of-structures (``"aos"``, ``"zyxf"``) layout has no equivalent layout policy in the C++ standard,
    so it can only be mapped onto ``layout_stride``.

    .. _extents: https://en.cppreference.com/w/cpp/container/mdspan/extents
    .. _layout_policy: https://en.cppreference.com/w/cpp/named_req/LayoutMappingPolicy
    .. _std::layout_left: https://en.cppreference.com/w/cpp/container/mdspan/layout_left
    .. _std::layout_right: https://en.cppreference.com/w/cpp/container/mdspan/layout_right
    .. _std::layout_stride: https://en.cppreference.com/w/cpp/container/mdspan/layout_stride

    Args:
        T: Element type of the mdspan
    """

    dynamic_extent = "std::dynamic_extent"

    _namespace = "std"
    _template = cpptype("std::mdspan< {T}, {extents}, {layout_policy} >", "<mdspan>")

    @classmethod
    def configure(cls, namespace: str = "std", header: str | HeaderFile = "<mdspan>"):
        """Configure the namespace and header ``std::mdspan`` is defined in."""
        cls._namespace = namespace
        cls._template = cpptype(
            f"{namespace}::mdspan< {{T}}, {{extents}}, {{layout_policy}} >", header
        )

    def __init__(
        self,
        T: UserTypeSpec,
        extents: tuple[int | str, ...],
        index_type: UserTypeSpec = PsUnsignedIntegerType(64),
        layout_policy: str | None = None,
        ref: bool = False,
        const: bool = False,
    ):
        T = create_type(T)

        extents_type_str = create_type(index_type).c_string()
        extents_str = f"{self._namespace}::extents< {extents_type_str}, {', '.join(str(e) for e in extents)} >"

        if layout_policy is None:
            layout_policy = f"{self._namespace}::layout_stride"
        elif layout_policy in ("layout_left", "layout_right", "layout_stride"):
            layout_policy = f"{self._namespace}::{layout_policy}"

        dtype = self._template(
            T=T, extents=extents_str, layout_policy=layout_policy, const=const
        )

        if ref:
            dtype = Ref(dtype)
        super().__init__(dtype)

        self._extents_type = extents_str
        self._layout_type = layout_policy
        self._dim = len(extents)

    @property
    def extents_type(self) -> str:
        return self._extents_type

    @property
    def layout_type(self) -> str:
        return self._layout_type

    def extent(self, r: int | ExprLike) -> AugExpr:
        return AugExpr.format("{}.extent({})", self, r)

    def stride(self, r: int | ExprLike) -> AugExpr:
        return AugExpr.format("{}.stride({})", self, r)

    def data_handle(self) -> AugExpr:
        return AugExpr.format("{}.data_handle()", self)

    def get_extraction(self) -> IFieldExtraction:
        mdspan = self

        class Extraction(IFieldExtraction):
            def ptr(self) -> AugExpr:
                return mdspan.data_handle()

            def size(self, coordinate: int) -> AugExpr | None:
                if coordinate > mdspan._dim:
                    return None
                else:
                    return mdspan.extent(coordinate)

            def stride(self, coordinate: int) -> AugExpr | None:
                if coordinate > mdspan._dim:
                    return None
                else:
                    return mdspan.stride(coordinate)

        return Extraction()

    @staticmethod
    def from_field(
        field: Field,
        extents_type: UserTypeSpec = PsUnsignedIntegerType(64),
        layout_policy: str | None = None,
        ref: bool = False,
        const: bool = False,
    ):
        """Creates a `std::mdspan` instance for a given pystencils field."""
        extents: list[str | int] = []

        for s in field.spatial_shape:
            extents.append(
                StdMdspan.dynamic_extent if isinstance(s, Symbol) else cast(int, s)
            )

        for s in field.index_shape:
            extents.append(StdMdspan.dynamic_extent if isinstance(s, Symbol) else s)

        return StdMdspan(
            field.dtype,
            tuple(extents),
            index_type=extents_type,
            layout_policy=layout_policy,
            ref=ref,
            const=const,
        ).var(field.name)


def mdspan_ref(field: Field, extents_type: PsType = PsUnsignedIntegerType(64)):
    from warnings import warn

    warn(
        "`mdspan_ref` is deprecated and will be removed in version 0.1. Use `std.mdspan.from_field` instead.",
        FutureWarning,
    )
    return StdMdspan.from_field(field, extents_type, ref=True)
