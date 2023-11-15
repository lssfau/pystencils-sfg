from __future__ import annotations
from typing import TYPE_CHECKING, Sequence, Set, Tuple

from abc import ABC, abstractmethod
from itertools import chain

from ..kernel_namespace import SfgKernelHandle
from ..source_concepts.source_objects import SrcObject, TypedSymbolOrObject
from ..exceptions import SfgException

if TYPE_CHECKING:
    from ..context import SfgContext
    from ..source_components import SfgHeaderInclude


class SfgCallTreeNode(ABC):
    """Base class for all nodes comprising SFG call trees. """
    def __init__(self, *children: SfgCallTreeNode):
        self._children = children

    @property
    def children(self) -> Tuple[SfgCallTreeNode]:
        return self._children

    def child(self, idx: int) -> SfgCallTreeNode:
        return self._children[idx]

    @children.setter
    def children(self, cs: Sequence[SfgCallTreeNode]) -> None:
        if len(cs) != len(self._children):
            raise ValueError("The number of child nodes must remain the same!")
        self._children = list(cs)

    def __getitem__(self, idx: int) -> SfgCallTreeNode:
        return self._children[idx]

    def __setitem__(self, idx: int, c: SfgCallTreeNode) -> None:
        self._children[idx] = c

    @abstractmethod
    def get_code(self, ctx: SfgContext) -> str:
        """Returns the code of this node.

        By convention, the code block emitted by this function should not contain a trailing newline.
        """
        pass

    @property
    def required_includes(self) -> Set[SfgHeaderInclude]:
        return set()


class SfgCallTreeLeaf(SfgCallTreeNode, ABC):

    @property
    @abstractmethod
    def required_parameters(self) -> Set[TypedSymbolOrObject]:
        pass


class SfgStatements(SfgCallTreeLeaf):
    """Represents (a sequence of) statements in the source language.

    This class groups together arbitrary code strings
    (e.g. sequences of C++ statements, cf. https://en.cppreference.com/w/cpp/language/statements),
    and annotates them with the set of symbols read and written by these statements.

    It is the user's responsibility to ensure that the code string is valid code in the output language,
    and that the lists of required and defined objects are correct and complete.

    Args:
        code_string: Code to be printed out.
        defined_objects: Objects (as `SrcObject` or `TypedSymbol`) that will be newly defined and visible to
            code in sequence after these statements.
        required_objects: Objects (as `SrcObject` or `TypedSymbol`) that are required as input to these statements.
    """

    def __init__(self,
                 code_string: str,
                 defined_params: Sequence[TypedSymbolOrObject],
                 required_params: Sequence[TypedSymbolOrObject]):
        super().__init__()

        self._code_string = code_string

        self._defined_params = set(defined_params)
        self._required_params = set(required_params)

        self._required_includes = set()
        for obj in chain(required_params, defined_params):
            if isinstance(obj, SrcObject):
                self._required_includes |= obj.required_includes

    @property
    def required_parameters(self) -> Set[TypedSymbolOrObject]:
        return self._required_params

    @property
    def defined_parameters(self) -> Set[TypedSymbolOrObject]:
        return self._defined_params

    @property
    def required_includes(self) -> Set[SfgHeaderInclude]:
        return self._required_includes

    def get_code(self, ctx: SfgContext) -> str:
        return self._code_string


class SfgSequence(SfgCallTreeNode):
    def __init__(self, children: Sequence[SfgCallTreeNode]):
        super().__init__(*children)

    def get_code(self, ctx: SfgContext) -> str:
        return "\n".join(c.get_code(ctx) for c in self._children)


class SfgBlock(SfgCallTreeNode):
    def __init__(self, subtree: SfgCallTreeNode):
        super().__init__(subtree)

    @property
    def subtree(self) -> SfgCallTreeNode:
        return self._children[0]

    def get_code(self, ctx: SfgContext) -> str:
        subtree_code = ctx.codestyle.indent(self._subtree.get_code(ctx))

        return "{\n" + subtree_code + "\n}"


class SfgKernelCallNode(SfgCallTreeLeaf):
    def __init__(self, kernel_handle: SfgKernelHandle):
        super().__init__()
        self._kernel_handle = kernel_handle

    @property
    def required_parameters(self) -> Set[TypedSymbolOrObject]:
        return set(p.symbol for p in self._kernel_handle.parameters)

    def get_code(self, ctx: SfgContext) -> str:
        ast_params = self._kernel_handle.parameters
        fnc_name = self._kernel_handle.fully_qualified_name
        call_parameters = ", ".join([p.symbol.name for p in ast_params])

        return f"{fnc_name}({call_parameters});"
