from ..context import SfgContext
from ..visitors import visitor
from ..source_components import (
    SfgClass,
    SfgConstructor,
    SfgMemberVariable,
    SfgMethod,
    SfgVisibility,
)
from ..exceptions import SfgException


class ClassDeclarationPrinter:
    def __init__(self, ctx: SfgContext):
        self._codestyle = ctx.codestyle

    def print(self, cls: SfgClass):
        return self.visit(cls, cls)

    @visitor
    def visit(self, obj: object, cls: SfgClass) -> str:
        raise SfgException("Can't print this.")

    @visit.case(SfgClass)
    def sfg_class(self, cls: SfgClass, _: SfgClass):
        code = f"{cls.class_keyword} {cls.class_name} \n"

        if cls.base_classes:
            code += f" : {','.join(cls.base_classes)}\n"

        code += "{\n"
        for visibility in (
            SfgVisibility.DEFAULT,
            SfgVisibility.PUBLIC,
            SfgVisibility.PRIVATE,
        ):
            if visibility != SfgVisibility.DEFAULT:
                code += f"\n{visibility}:\n"
            for member in cls.members(visibility):
                code += self._codestyle.indent(self.visit(member, cls)) + "\n"
        code += "};\n"

        return code

    @visit.case(SfgConstructor)
    def sfg_constructor(self, constr: SfgConstructor, cls: SfgClass):
        code = f"{cls.class_name} ("
        code += ", ".join(f"{param.dtype} {param.name}" for param in constr.parameters)
        code += ")\n"
        if constr.initializers:
            code += "  : " + ", ".join(constr.initializers) + "\n"
        if constr.body:
            code += "{\n" + self._codestyle.indent(constr.body) + "\n}\n"
        else:
            code += "{ }\n"
        return code

    @visit.case(SfgMemberVariable)
    def sfg_member_var(self, var: SfgMemberVariable, _: SfgClass):
        return f"{var.dtype} {var.name};"

    @visit.case(SfgMethod)
    def sfg_method(self, method: SfgMethod, _: SfgClass):
        code = f"void {method.name} ("
        code += ", ".join(f"{param.dtype} {param.name}" for param in method.parameters)
        code += ");"
        return code
