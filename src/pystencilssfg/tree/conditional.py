from __future__ import annotations
from typing import TYPE_CHECKING, Optional, cast, Generator, Sequence, NewType

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


class SfgSwitchCase(SfgCallTreeNode):
    DefaultCaseType = NewType("DefaultCaseType", object)
    Default = DefaultCaseType(object())

    def __init__(self, label: str | DefaultCaseType, body: SfgCallTreeNode):
        self._label = label
        super().__init__(body)

    @property
    def label(self) -> str | DefaultCaseType:
        return self._label

    @property
    def body(self) -> SfgCallTreeNode:
        return self._children[0]

    @property
    def is_default(self) -> bool:
        return self._label == SfgSwitchCase.Default

    def get_code(self, ctx: SfgContext) -> str:
        code = ""
        if self._label == SfgSwitchCase.Default:
            code += "default: {\n"
        else:
            code += f"case {self._label}: {{\n"
        code += ctx.codestyle.indent(self.body.get_code(ctx))
        code += "\nbreak;\n}"
        return code


class SfgSwitch(SfgCallTreeNode):
    def __init__(
        self,
        switch_arg: str | TypedSymbolOrObject,
        cases_dict: dict[str, SfgCallTreeNode],
        default: SfgCallTreeNode | None = None,
    ):
        children = [SfgSwitchCase(label, body) for label, body in cases_dict.items()]
        if default is not None:
            # invariant: the default case is always the last child
            children += [SfgSwitchCase(SfgSwitchCase.Default, default)]
        self._switch_arg = switch_arg
        self._default = default
        super().__init__(*children)

    @property
    def switch_arg(self) -> str | TypedSymbolOrObject:
        return self._switch_arg

    def cases(self) -> Generator[SfgCallTreeNode, None, None]:
        if self._default is not None:
            yield from self._children[:-1]
        else:
            yield from self._children

    @property
    def default(self) -> SfgCallTreeNode | None:
        return self._default

    @property
    def children(self) -> tuple[SfgCallTreeNode, ...]:
        return tuple(self._children)

    @children.setter
    def children(self, cs: Sequence[SfgCallTreeNode]) -> None:
        if len(cs) != len(self._children):
            raise ValueError("The number of child nodes must remain the same!")

        self._default = None
        for i, c in enumerate(cs):
            if not isinstance(c, SfgSwitchCase):
                raise ValueError(
                    "An SfgSwitch node can only have SfgSwitchCases as children."
                )
            if c.is_default:
                if i != len(cs) - 1:
                    raise ValueError("Default case must be listed last.")
                else:
                    self._default = c

        self._children = list(cs)

    def set_child(self, idx: int, c: SfgCallTreeNode):
        if not isinstance(c, SfgSwitchCase):
            raise ValueError(
                "An SfgSwitch node can only have SfgSwitchCases as children."
            )

        if c.is_default:
            if idx != len(self._children) - 1:
                raise ValueError("Default case must be the last child.")
            elif self._default is None:
                raise ValueError("Cannot replace normal case with default case.")
            else:
                self._default = c
                self._children[-1] = c
        else:
            self._children[idx] = c

    def get_code(self, ctx: SfgContext) -> str:
        code = f"switch({self._switch_arg}) {{\n"
        code += "\n".join(c.get_code(ctx) for c in self.children)
        code += "}"
        return code
