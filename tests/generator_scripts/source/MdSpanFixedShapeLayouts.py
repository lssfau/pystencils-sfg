import pystencils as ps
from pystencilssfg import SourceFileGenerator
from pystencilssfg.lang.cpp import std
from pystencilssfg.lang import strip_ptr_ref

std.mdspan.configure(namespace="std::experimental", header="<experimental/mdspan>")

with SourceFileGenerator() as sfg:
    sfg.namespace("gen")
    sfg.include("<cassert>")

    def check_layout(field: ps.Field, mdspan: std.mdspan):
        seq = []

        for d in range(field.spatial_dimensions + field.index_dimensions):
            seq += [
                sfg.expr(
                    'assert({} == {} && "Shape mismatch at coordinate {}");',
                    mdspan.extent(d),
                    field.shape[d],
                    d,
                ),
                sfg.expr(
                    'assert({} == {} && "Stride mismatch at coordinate {}");',
                    mdspan.stride(d),
                    field.strides[d],
                    d,
                ),
            ]

        return seq

    f_soa = ps.fields("f_soa(9): double[17, 19, 32]", layout="soa")
    f_soa_mdspan = std.mdspan.from_field(f_soa, layout_policy="layout_left", ref=True)

    sfg.code(f"using field_soa = {strip_ptr_ref(f_soa_mdspan.dtype)};")
    sfg.function("checkLayoutSoa")(
        *check_layout(f_soa, f_soa_mdspan)
    )

    f_aos = ps.fields("f_aos(9): double[17, 19, 32]", layout="aos")
    f_aos_mdspan = std.mdspan.from_field(f_aos, ref=True)
    sfg.code(f"using field_aos = {strip_ptr_ref(f_aos_mdspan.dtype)};")

    sfg.function("checkLayoutAos")(
        *check_layout(f_aos, f_aos_mdspan)
    )

    f_c = ps.fields("f_c(9): double[17, 19, 32]", layout="c")
    f_c_mdspan = std.mdspan.from_field(f_c, layout_policy="layout_right", ref=True)
    sfg.code(f"using field_c = {strip_ptr_ref(f_c_mdspan.dtype)};")

    sfg.function("checkLayoutC")(
        *check_layout(f_c, f_c_mdspan)
    )
