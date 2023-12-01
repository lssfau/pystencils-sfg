# type: ignore
from pystencilssfg import SourceFileGenerator, SfgConfiguration
from pystencilssfg.configuration import SfgCodeStyle
from pystencilssfg.source_concepts import SrcObject
from pystencilssfg.source_components import SfgClass, SfgMemberVariable, SfgConstructor, SfgMethod, SfgVisibility

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

with SourceFileGenerator(sfg_config) as sfg:

    @kernel
    def assignments():
        f[0,0] @= 3 * g[0,0]

    khandle = sfg.kernels.create(assignments)

    cls = SfgClass("MyClass")
    cls.add_method(SfgMethod(
        "callKernel",
        sfg.call(khandle),
        visibility=SfgVisibility.PUBLIC
    ))

    cls.add_member_variable(
        SfgMemberVariable(
            "stuff", "std::vector< int >",
            SfgVisibility.PRIVATE
        )
    )

    cls.add_constructor(
        SfgConstructor(
            [SrcObject("std::vector< int > &", "stuff")],
            ["stuff_(stuff)"],
            visibility=SfgVisibility.PUBLIC
        )
    )

    sfg.context.add_class(cls)
