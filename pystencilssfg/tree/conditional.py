from __future__ import annotations
from typing import TYPE_CHECKING, Optional, cast

from .basic_nodes import SfgCallTreeNode, SfgCallTreeLeaf
from ..source_concepts.source_objects import TypedSymbolOrObject

if TYPE_CHECKING:
    from ..context import SfgContext


class SfgCondition(SfgCallTreeLeaf):
    pass


class SfgCustomCondition(SfgCondition):
    def __init__(self, cond_text: str):
        super().__init__()
        self._cond_text = cond_text

    @property
    def required_parameters(self) -> set[TypedSymbolOrObject]:
        return set()

    def get_code(self, ctx: SfgContext) -> str:
        return self._cond_text


# class IntEven(SfgCondition):
#     def __init__(self, )


class SfgBranch(SfgCallTreeNode):
    def __init__(self,
                 cond: SfgCondition,
                 branch_true: SfgCallTreeNode,
                 branch_false: Optional[SfgCallTreeNode] = None):
        super().__init__(cond, branch_true, *((branch_false,) if branch_false else ()))

    @property
    def condition(self) -> SfgCondition:
        return cast(SfgCondition, self._children[0])

    @property
    def branch_true(self) -> SfgCallTreeNode:
        return self._children[1]

    @property
    def branch_false(self) -> SfgCallTreeNode:
        return self._children[2]

    def get_code(self, ctx: SfgContext) -> str:
        code = f"if({self.condition.get_code(ctx)}) {{\n"
        code += ctx.codestyle.indent(self.branch_true.get_code(ctx))
        code += "\n}"

        if self.branch_false is not None:
            code += "else {\n"
            code += ctx.codestyle.indent(self.branch_false.get_code(ctx))
            code += "\n}"

        return code
