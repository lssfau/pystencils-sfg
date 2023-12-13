from __future__ import annotations
from typing import TYPE_CHECKING, Optional, cast, Generator

from pystencils.typing import TypedSymbol, BasicType

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


class IntEven(SfgCondition):
    def __init__(self, symbol: TypedSymbol):
        super().__init__()
        if not isinstance(symbol.dtype, BasicType) or not symbol.dtype.is_int():
            raise ValueError(f"Symbol {symbol} does not have integer type.")

        self._symbol = symbol

    @property
    def required_parameters(self) -> set[TypedSymbolOrObject]:
        return {self._symbol}

    def get_code(self, ctx: SfgContext) -> str:
        return f"(({self._symbol.name} & 1) ^ 1)"


class IntOdd(SfgCondition):
    def __init__(self, symbol: TypedSymbol):
        super().__init__()
        if not isinstance(symbol.dtype, BasicType) or not symbol.dtype.is_int():
            raise ValueError(f"Symbol {symbol} does not have integer type.")

        self._symbol = symbol

    @property
    def required_parameters(self) -> set[TypedSymbolOrObject]:
        return {self._symbol}

    def get_code(self, ctx: SfgContext) -> str:
        return f"({self._symbol.name} & 1)"


class SfgBranch(SfgCallTreeNode):
    def __init__(
        self,
        cond: SfgCondition,
        branch_true: SfgCallTreeNode,
        branch_false: Optional[SfgCallTreeNode] = None,
    ):
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


class SfgSwitch(SfgCallTreeNode):
    def __init__(
        self,
        switch_arg: str | TypedSymbolOrObject,
        cases_dict: dict[str, SfgCallTreeNode],
        default: SfgCallTreeNode | None = None,
    ):
        children = tuple(cases_dict.values()) + (
            (default,) if default is not None else ()
        )
        super().__init__(*children)
        self._switch_arg = switch_arg
        self._cases_dict = cases_dict
        self._default = default

    @property
    def switch_arg(self) -> str | TypedSymbolOrObject:
        return self._switch_arg

    def cases(self) -> Generator[tuple[str, SfgCallTreeNode], None, None]:
        yield from self._cases_dict.items()

    @property
    def default(self) -> SfgCallTreeNode | None:
        return self._default

    def get_code(self, ctx: SfgContext) -> str:
        code = f"switch({self._switch_arg}) {{\n"
        for label, subtree in self._cases_dict.items():
            code += f"case {label}: {{\n"
            code += ctx.codestyle.indent(subtree.get_code(ctx))
            code += "\nbreak;\n}\n"

        if self._default is not None:
            code += "default: {\n"
            code += ctx.codestyle.indent(self._default.get_code(ctx))
            code += "\nbreak;\n}\n"

        code += "}"
        return code
