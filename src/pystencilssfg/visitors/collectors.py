from __future__ import annotations

from typing import TYPE_CHECKING

from functools import reduce

from .dispatcher import visitor
from ..exceptions import SfgException
from ..tree import SfgCallTreeNode
from ..source_components import SfgFunction, SfgClass, SfgConstructor, SfgMemberVariable

if TYPE_CHECKING:
    from ..source_components import SfgHeaderInclude


class CollectIncludes:
    @visitor
    def visit(self, obj: object) -> set[SfgHeaderInclude]:
        raise SfgException(f"Can't collect includes from object of type {type(obj)}")

    @visit.case(SfgCallTreeNode)
    def tree_node(self, node: SfgCallTreeNode) -> set[SfgHeaderInclude]:
        return reduce(
            lambda accu, child: accu | self.visit(child), node.children, node.required_includes
        )

    @visit.case(SfgFunction)
    def sfg_function(self, func: SfgFunction) -> set[SfgHeaderInclude]:
        return self.visit(func.tree)

    @visit.case(SfgClass)
    def sfg_class(self, cls: SfgClass) -> set[SfgHeaderInclude]:
        return reduce(
            lambda accu, member: accu | (self.visit(member)), cls.members(), set()
        )

    @visit.case(SfgConstructor)
    def sfg_constructor(self, constr: SfgConstructor) -> set[SfgHeaderInclude]:
        return reduce(
            lambda accu, obj: accu | obj.required_includes, constr.parameters, set()
        )

    @visit.case(SfgMemberVariable)
    def sfg_member_var(self, var: SfgMemberVariable) -> set[SfgHeaderInclude]:
        return var.required_includes
