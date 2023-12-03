from __future__ import annotations

from textwrap import indent
from itertools import chain, repeat

from ..context import SfgContext
from ..configuration import SfgOutputSpec
from ..visitors import visitor
from ..exceptions import SfgException

from ..source_components import (
    SfgEmptyLines, SfgHeaderInclude
)


def interleave(*iters):
    try:
        for iter in iters:
            yield next(iter)
    except StopIteration:
        pass


class SfgHeaderPrinter:
    def __init__(self, output_spec: SfgOutputSpec):
        self._output_spec = output_spec

    def code_string(self, ctx: SfgContext) -> str:
        return self.visit(ctx)

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

    @visit.case(SfgContext)
    def frame(self, ctx: SfgContext) -> str:
        code = ""

        if ctx.prelude_comment:
            code += "/*\n" + indent(ctx.prelude_comment, "* ", predicate=lambda _: True) + "*/\n"

        code += "\n#pragma once\n\n"

        includes = filter(lambda incl: not incl.private, ctx.includes())
        code += "\n".join(self.visit(incl) for incl in includes)
        code += "\n"

        fq_namespace = ctx.fully_qualified_namespace
        if fq_namespace is not None:
            code += f"namespace {fq_namespace} {{\n"

        parts = interleave(
            chain(
                ctx.definitions(),
                ctx.classes(),
                ctx.functions()
            ),
            repeat(SfgEmptyLines(1))
        )

        code += "".join(self.visit(p) for p in parts)

        if fq_namespace is not None:
            code += f"}} \\ namespace {fq_namespace}\n"

        return code
