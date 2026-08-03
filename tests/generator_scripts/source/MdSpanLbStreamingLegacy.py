import numpy as np
import pystencils as ps
from pystencilssfg import SourceFileGenerator, SfgComposer
from pystencilssfg.lang.cpp import std
from pystencilssfg.lang import strip_ptr_ref

std.mdspan.configure(namespace="std::experimental", header="<experimental/mdspan>")

stencil = ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1))


def lbm_stream(sfg: SfgComposer, field_layout: str, layout_policy: str):
    src, dst = ps.fields("src(6), dst(6): double[3D]", layout=field_layout)

    src_mdspan = std.mdspan.from_field(src, layout_policy=layout_policy, extents_type="int64", ref=True)
    dst_mdspan = std.mdspan.from_field(dst, layout_policy=layout_policy, extents_type="int64", ref=True)

    asms = []
    asms_zero = []

    for i, dir in enumerate(stencil):
        asms.append(ps.Assignment(dst.center(i), src[-np.array(dir)](i)))
        asms_zero.append(ps.Assignment(dst.center(i), 0))

    khandle = sfg.kernels.create(asms, f"stream_{field_layout}")
    khandle_zero = sfg.kernels.create(asms_zero, f"zero_{field_layout}")

    sfg.code(f"using field_{field_layout} = {strip_ptr_ref(src_mdspan.get_dtype())};")

    sfg.klass(f"Kernel_{field_layout}")(
        sfg.public(
            sfg.method("operator()")(
                sfg.map_field(src, src_mdspan),
                sfg.map_field(dst, dst_mdspan),
                sfg.call(khandle),
            ),

            sfg.method("setZero")(
                sfg.map_field(dst, dst_mdspan),
                sfg.call(khandle_zero),
            )
        )
    )


with SourceFileGenerator() as sfg:
    sfg.namespace("gen")
    sfg.include("<cassert>")
    sfg.include("<array>")

    stencil_code = (
        "{{"
        + ", ".join("{" + ", ".join(str(ci) for ci in c) + "}" for c in stencil)
        + "}}"
    )
    sfg.code(
        f"constexpr std::array< std::array< int64_t, 3 >, 6 > STENCIL = {stencil_code};"
    )

    lbm_stream(sfg, "fzyx", "layout_left")
    lbm_stream(sfg, "c", "layout_right")
    lbm_stream(sfg, "zyxf", "layout_stride")
