from pystencils import TypedSymbol, fields, kernel

from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:
    N = 10
    α = TypedSymbol("alpha", "float32")
    src, dst = fields(f"src, dst: float32[{N}]")

    @kernel
    def scale():
        src[0] @= α * dst.center()

    khandle = sfg.kernels.create(scale)

    sfg.namespace("gen")
    sfg.code(f"constexpr int N = {N};")

    sfg.klass("Scale")(
        sfg.private(α),
        sfg.public(
            sfg.constructor(α).init(α)(α),
            sfg.method("operator()")(sfg.init(α)(f"this->{α}"), sfg.call(khandle)),
        ),
    )
