# type: ignore
from pystencilssfg import SourceFileGenerator, SfgConfiguration, SfgComposer
from pystencilssfg.configuration import SfgCodeStyle
from pystencilssfg.composer import SfgClassComposer
from pystencilssfg.source_concepts import SrcObject

from pystencils import fields, kernel

sfg_config = SfgConfiguration(
    output_directory="out/test_class_composer",
    outer_namespace="gen_code",
    codestyle=SfgCodeStyle(
        code_style="Mozilla",
        force_clang_format=True
    )
)

f, g = fields("f, g(1): double[2D]")

with SourceFileGenerator(sfg_config) as ctx:
    sfg = SfgComposer(ctx)
    c = SfgClassComposer(ctx)

    @kernel
    def assignments():
        f[0, 0] @= 3 * g[0, 0]

    khandle = sfg.kernels.create(assignments)

    c.struct("DataStruct")(
        SrcObject("coord", "uint32_t"),
        SrcObject("value", "float")
    ),

    c.klass("MyClass", bases=("MyBaseClass",))(
        # class body sequencer

        c.constructor(SrcObject("a", "int"))
        .init("a_(a)")
        .body(
            'cout << "Hi!" << endl;'
        ),

        c.private(
            c.var("a_", "int"),

            c.method("getX", returns="int")(
                "return 2.0;"
            )
        ),

        c.public(
            "using xtype = uint8_t;"
        )
    )
