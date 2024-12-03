from pystencils import TypedSymbol, fields, kernel

from pystencilssfg import SourceFileGenerator

with SourceFileGenerator() as sfg:
    α = TypedSymbol("alpha", "float32")
    f, g = fields("f, g: float32[10]")

    @kernel
    def scale():
        f[0] @= α * g.center()

    khandle = sfg.kernels.create(scale)

    sfg.klass("Scale")(
        sfg.private(α),
        sfg.public(
            sfg.constructor(α).init(α)(α.name),
            sfg.method("operator()")(sfg.init(α)(f"this->{α}"), sfg.call(khandle)),
        ),
    )
