from __future__ import annotations

from textwrap import indent
from itertools import chain, repeat, cycle

from pystencils.astnodes import KernelFunction
from pystencils import Backend
from pystencils.backends import generate_c

from ..context import SfgContext
from ..configuration import SfgOutputSpec
from ..visitors import visitor
from ..exceptions import SfgException

from ..source_components import (
    SfgEmptyLines,
    SfgHeaderInclude,
    SfgKernelNamespace,
    SfgFunction,
    SfgClass,
    SfgInClassDefinition,
    SfgConstructor,
    SfgMemberVariable,
    SfgMethod,
    SfgVisibility,
    SfgVisibilityBlock
)


def interleave(*iters):
    try:
        for iter in cycle(iters):
            yield next(iter)
    except StopIteration:
        pass


class SfgGeneralPrinter:
    @visitor
    def visit(self, obj: object) -> str:
        raise SfgException(f"Can't print object of type {type(obj)}")

    @visit.case(SfgEmptyLines)
    def emptylines(self, el: SfgEmptyLines) -> str:
        return "\n" * el.lines

    @visit.case(str)
    def string(self, s: str) -> str:
        return s

    @visit.case(SfgHeaderInclude)
    def include(self, incl: SfgHeaderInclude) -> str:
        if incl.system_header:
            return f"#include <{incl.file}>"
        else:
            return f'#include "{incl.file}"'

    def prelude(self, ctx: SfgContext) -> str:
        if ctx.prelude_comment:
            return (
                "/*\n"
                + indent(ctx.prelude_comment, "* ", predicate=lambda _: True)
                + "*/\n"
            )
        else:
            return ""

    def param_list(self, func: SfgFunction) -> str:
        params = sorted(list(func.parameters), key=lambda p: p.name)
        return ", ".join(f"{param.dtype} {param.name}" for param in params)


class SfgHeaderPrinter(SfgGeneralPrinter):
    def __init__(self, ctx: SfgContext, output_spec: SfgOutputSpec):
        self._output_spec = output_spec
        self._ctx = ctx

    def get_code(self) -> str:
        return self.visit(self._ctx)

    @visitor
    def visit(self, obj: object) -> str:
        return super().visit(obj)

    @visit.case(SfgContext)
    def frame(self, ctx: SfgContext) -> str:
        code = super().prelude(ctx)

        code += "\n#pragma once\n\n"

        includes = filter(lambda incl: not incl.private, ctx.includes())
        code += "\n".join(self.visit(incl) for incl in includes)
        code += "\n\n"

        fq_namespace = ctx.fully_qualified_namespace
        if fq_namespace is not None:
            code += f"namespace {fq_namespace} {{\n\n"

        parts = interleave(ctx.declarations_ordered(), repeat(SfgEmptyLines(1)))

        code += "\n".join(self.visit(p) for p in parts)

        if fq_namespace is not None:
            code += f"}} // namespace {fq_namespace}\n"

        return code

    @visit.case(SfgFunction)
    def function(self, func: SfgFunction):
        params = sorted(list(func.parameters), key=lambda p: p.name)
        param_list = ", ".join(f"{param.dtype} {param.name}" for param in params)
        return f"{func.return_type} {func.name} ( {param_list} );"

    @visit.case(SfgClass)
    def sfg_class(self, cls: SfgClass):
        code = f"{cls.class_keyword} {cls.class_name} \n"

        if cls.base_classes:
            code += f" : {','.join(cls.base_classes)}\n"

        code += "{\n"

        for block in cls.visibility_blocks():
            code += self.visit(block) + "\n"

        code += "};\n"

        return code

    @visit.case(SfgVisibilityBlock)
    def vis_block(self, block: SfgVisibilityBlock) -> str:
        code = ""
        if block.visibility != SfgVisibility.DEFAULT:
            code += f"{block.visibility}:\n"
        code += self._ctx.codestyle.indent(
            "\n".join(self.visit(m) for m in block.members())
        )
        return code

    @visit.case(SfgInClassDefinition)
    def sfg_inclassdef(self, definition: SfgInClassDefinition):
        return definition.text

    @visit.case(SfgConstructor)
    def sfg_constructor(self, constr: SfgConstructor):
        code = f"{constr.owning_class.class_name} ("
        code += ", ".join(f"{param.dtype} {param.name}" for param in constr.parameters)
        code += ")\n"
        if constr.initializers:
            code += "  : " + ", ".join(constr.initializers) + "\n"
        if constr.body:
            code += "{\n" + self._ctx.codestyle.indent(constr.body) + "\n}\n"
        else:
            code += "{ }\n"
        return code

    @visit.case(SfgMemberVariable)
    def sfg_member_var(self, var: SfgMemberVariable):
        return f"{var.dtype} {var.name};"

    @visit.case(SfgMethod)
    def sfg_method(self, method: SfgMethod):
        code = f"{method.return_type} {method.name} ({self.param_list(method)})"
        code += "const" if method.const else ""
        if method.inline:
            code += (
                " {\n"
                + self._ctx.codestyle.indent(method.tree.get_code(self._ctx))
                + "}\n"
            )
        else:
            code += ";"
        return code


def delimiter(content):
    return f"""\
/*************************************************************************************
 *                                {content}
*************************************************************************************/
"""


class SfgImplPrinter(SfgGeneralPrinter):
    def __init__(self, ctx: SfgContext, output_spec: SfgOutputSpec):
        self._output_spec = output_spec
        self._ctx = ctx

    def get_code(self) -> str:
        return self.visit(self._ctx)

    @visitor
    def visit(self, obj: object) -> str:
        return super().visit(obj)

    @visit.case(SfgContext)
    def frame(self, ctx: SfgContext) -> str:
        code = super().prelude(ctx)

        code += f'\n#include "{self._output_spec.get_header_filename()}"\n\n'

        includes = filter(lambda incl: incl.private, ctx.includes())
        code += "\n".join(self.visit(incl) for incl in includes)

        code += "\n\n#define FUNC_PREFIX inline\n\n"

        fq_namespace = ctx.fully_qualified_namespace
        if fq_namespace is not None:
            code += f"namespace {fq_namespace} {{\n\n"

        parts = interleave(
            chain(
                [delimiter("Kernels")],
                ctx.kernel_namespaces(),
                [delimiter("Functions")],
                ctx.functions(),
                [delimiter("Class Methods")],
                ctx.classes(),
            ),
            repeat(SfgEmptyLines(1)),
        )

        code += "\n".join(self.visit(p) for p in parts)

        if fq_namespace is not None:
            code += f"}} // namespace {fq_namespace}\n"

        return code

    @visit.case(SfgKernelNamespace)
    def kernel_namespace(self, kns: SfgKernelNamespace) -> str:
        code = f"namespace {kns.name} {{\n\n"
        code += "\n\n".join(self.visit(ast) for ast in kns.asts)
        code += f"\n}} // namespace {kns.name}\n"
        return code

    @visit.case(KernelFunction)
    def kernel(self, kfunc: KernelFunction) -> str:
        return generate_c(kfunc, dialect=Backend.C)

    @visit.case(SfgFunction)
    def function(self, func: SfgFunction) -> str:
        code = f"{func.return_type} {func.name} ({self.param_list(func)})"
        code += (
            "{\n" + self._ctx.codestyle.indent(func.tree.get_code(self._ctx)) + "}\n"
        )
        return code

    @visit.case(SfgClass)
    def sfg_class(self, cls: SfgClass) -> str:
        methods = filter(lambda m: not m.inline, cls.methods())
        return "\n".join(self.visit(m) for m in methods)

    @visit.case(SfgMethod)
    def sfg_method(self, method: SfgMethod) -> str:
        const_qual = "const" if method.const else ""
        code = f"{method.return_type} {method.owning_class.class_name}::{method.name}"
        code += f"({self.param_list(method)}) {const_qual}"
        code += (
            " {\n" + self._ctx.codestyle.indent(method.tree.get_code(self._ctx)) + "}\n"
        )
        return code
