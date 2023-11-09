from __future__ import annotations
from typing import TYPE_CHECKING, Sequence, Optional

if TYPE_CHECKING:
    from ..context import SfgContext

from jinja2.filters import do_indent
from pystencils.typing import TypedSymbol

from .basic_nodes import SfgCallTreeNode, SfgCallTreeLeaf

class SfgCondition(SfgCallTreeLeaf):
    pass

class SfgCustomCondition(SfgCondition):
    def __init__(self, cond_text: str):
        self._cond_text = cond_text

    def required_symbols(self) -> set(TypedSymbol):
        return set()

    def get_code(self, ctx: SfgContext) -> str:
        return self._cond_text
    

# class IntEven(SfgCondition):
#     def __init__(self, )


class SfgBranch(SfgCallTreeNode):
    def __init__(self, cond: SfgCondition, branch_true: SfgCallTreeNode, branch_false: Optional[SfgCallTreeNode] = None):
        self._cond = cond
        self._branch_true = branch_true
        self._branch_false = branch_false
    
    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        if self._branch_false is not None:
            return (self._branch_true, self._branch_false)
        else:
            return (self._branch_true,)
        
    def get_code(self, ctx: SfgContext) -> str:
        code = f"if({self._cond.get_code(ctx)}) {{\n"
        code += ctx.codestyle.indent(self._branch_true.get_code(ctx))
        code += "\n}"
        
        if self._branch_false is not None:
            code += "else {\n"
            code += ctx.codestyle.indent(self._branch_false.get_code(ctx))
            code += "\n}"

        return code
    
