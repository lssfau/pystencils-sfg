from __future__ import annotations

from typing import TYPE_CHECKING

from functools import reduce

from ..exceptions import SfgException
from ..ir import SfgCallTreeNode
from ..ir.source_components import (
    SfgFunction,
    SfgClass,
    SfgConstructor,
    SfgMemberVariable,
    SfgInClassDefinition,
)
from ..context import SfgContext

if TYPE_CHECKING:
    from ..ir.source_components import SfgHeaderInclude


class CollectIncludes:
    def __call__(self, obj: object) -> set[SfgHeaderInclude]:
        return self.visit(obj)

    def visit(self, obj: object) -> set[SfgHeaderInclude]:
        match obj:
            case SfgContext():
                includes = set()
                for func in obj.functions():
                    includes |= self.visit(func)

                for cls in obj.classes():
                    includes |= self.visit(cls)

                return includes

            case SfgCallTreeNode():
                return reduce(
                    lambda accu, child: accu | self.visit(child),
                    obj.children,
                    obj.required_includes,
                )

            case SfgFunction(_, tree, _):
                return self.visit(tree)

            case SfgClass():
                return reduce(
                    lambda accu, member: accu | (self.visit(member)),
                    obj.members(),
                    set(),
                )

            case SfgConstructor():
                return reduce(
                    lambda accu, obj: accu | obj.required_includes,
                    obj.parameters,
                    set(),
                )

            case SfgMemberVariable():
                return obj.required_includes

            case SfgInClassDefinition():
                return set()

            case _:
                raise SfgException(
                    f"Can't collect includes from object of type {type(obj)}"
                )


def prepare_context(ctx: SfgContext):
    """Prepares a populated context for printing. Make sure to run this function on the
    [SfgContext][pystencilssfg.SfgContext] before passing it to a printer.

    Steps:
     - Collection of includes: All defined functions and classes are traversed to collect all required
       header includes
    """

    #   Collect all includes
    required_includes = CollectIncludes().visit(ctx)
    for incl in required_includes:
        ctx.add_include(incl)

    return ctx
