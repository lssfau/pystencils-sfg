# type: ignore
from pystencilssfg import SourceFileGenerator, SfgConfiguration, SfgComposer
from pystencilssfg.configuration import SfgCodeStyle
from pystencils.types import PsCustomType
from pystencilssfg.ir.source_components import SfgClass, SfgMemberVariable, SfgConstructor, SfgMethod

from pystencils import fields, kernel

sfg_config = SfgConfiguration(
    output_directory="out/test_classes",
    outer_namespace="gen_code",
    codestyle=SfgCodeStyle(
        code_style="Mozilla",
        force_clang_format=True
    )
)

f, g = fields("f, g(1): double[2D]")

with SourceFileGenerator(sfg_config) as ctx:
    sfg = SfgComposer(ctx)

    @kernel
    def assignments():
        f[0,0] @= 3 * g[0,0]

    khandle = sfg.kernels.create(assignments)

    cls = SfgClass("MyClass")
    cls.default.append_member(SfgMethod(
        "callKernel",
        sfg.call(khandle)
    ))

    cls.default.append_member(SfgMethod(
        "inlineConst",
        sfg.seq(
            "return -1.0;"
        ),
        return_type="double",
        inline=True,
        const=True
    ))

    cls.default.append_member(SfgMethod(
        "awesomeMethod",
        sfg.seq(
            "return 2.0f;"
        ),
        return_type="float",
        inline=False,
        const=True
    ))

    cls.default.append_member(
        SfgMemberVariable(
            "stuff", PsCustomType("std::vector< int > &")
        )
    )

    cls.default.append_member(
        SfgConstructor(
            [sfg.var("stuff", PsCustomType("std::vector< int > &"))],
            ["stuff_(stuff)"]
        )
    )

    sfg.context.add_class(cls)
