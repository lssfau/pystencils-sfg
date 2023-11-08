from __future__ import annotations
from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from ..context import SfgContext

from abc import ABC, abstractmethod
from functools import reduce

from jinja2.filters import do_indent

from ..kernel_namespace import SfgKernelHandle

from pystencils.typing import TypedSymbol

class SfgCallTreeNode(ABC):
    """Base class for all nodes comprising SFG call trees. """

    @property
    @abstractmethod
    def children(self) -> Sequence[SfgCallTreeNode]:
        pass

    @abstractmethod
    def get_code(self, ctx: SfgContext) -> str:
        """Returns the code of this node.

        By convention, the code block emitted by this function should not contain a trailing newline.
        """
        pass


class SfgCallTreeLeaf(SfgCallTreeNode, ABC):
    
    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        return ()

    @property
    @abstractmethod
    def required_symbols(self) -> set(TypedSymbol):
        pass


class SfgParameterDefinition(SfgCallTreeLeaf):
    def __init__(self, defined_param: TypedSymbol, required_params: Set[TypedSymbol], code_string: str):
        self._defined_param = defined_param
        self._required_params = required_params
        self._code_string = code_string

    @property
    def defined_symbol(self) -> TypedSymbol:
        return self._defined_param

    @property
    def required_symbols(self) -> set(TypedSymbol):
        return self._required_params

    def get_code(self):
        return self._code_string


class SfgCustomStatement(SfgCallTreeLeaf):
    def __init__(self, statement: str):
        self._statement = statement

    def required_symbols(self) -> set(TypedSymbol):
        return set()
    
    def get_code(self, ctx: SfgContext) -> str:
        return self._statement


class SfgSequence(SfgCallTreeNode):
    def __init__(self, children: Sequence[SfgCallTreeNode]):
        self._children = tuple(children)

    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        return self._children
    
    def get_code(self, ctx: SfgContext) -> str:
        return "\n".join(c.get_code(ctx) for c in self._children)


class SfgBlock(SfgCallTreeNode):
    def __init__(self, subtree: SfgCallTreeNode):
        super().__init__(ctx)
        self._subtree = subtree

    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        return { self._subtree }
    
    def get_code(self, ctx: SfgContext) -> str:
        subtree_code = ctx.codestyle.indent(self._subtree.get_code(ctx))

        return "{\n" + subtree_code + "\n}"


class SfgKernelCallNode(SfgCallTreeLeaf):
    def __init__(self, kernel_handle: SfgKernelHandle):
        self._kernel_handle = kernel_handle

    @property
    def required_symbols(self) -> set(TypedSymbol):
        return set(p.symbol for p in self._kernel_handle.parameters)
    
    def get_code(self, ctx: SfgContext) -> str:
        ast_params = self._kernel_handle.parameters
        fnc_name = self._kernel_handle.fully_qualified_name
        call_parameters = ", ".join([p.symbol.name for p in ast_params])

        return f"{fnc_name}({call_parameters});"
