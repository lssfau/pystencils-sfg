from __future__ import annotations
from typing import TYPE_CHECKING, Sequence

from abc import ABC, abstractmethod
from itertools import chain

from ..source_components import SfgHeaderInclude, SfgKernelHandle
from ..source_concepts.source_objects import SrcObject, TypedSymbolOrObject

if TYPE_CHECKING:
    from ..context import SfgContext


class SfgCallTreeNode(ABC):
    """Base class for all nodes comprising SFG call trees.

    ## Code Printing

    For extensibility, code printing is implemented inside the call tree.
    Therefore, every instantiable call tree node must implement the method `get_code`.
    By convention, the string returned by `get_code` should not contain a trailing newline.

    ## Branching Structure

    The branching structure of the call tree is managed uniformly through the `children` interface
    of SfgCallTreeNode. Each subclass must ensure that access to and modification of
    the branching structure through the `children` property and the `child` and `set_child`
    methods is possible, if necessary by overriding the property and methods.
    """

    def __init__(self, *children: SfgCallTreeNode):
        self._children = list(children)

    @property
    def children(self) -> tuple[SfgCallTreeNode, ...]:
        """This node's children"""
        return tuple(self._children)

    @children.setter
    def children(self, cs: Sequence[SfgCallTreeNode]) -> None:
        """Replaces this node's children. By default, the number of child nodes must not change."""
        if len(cs) != len(self._children):
            raise ValueError("The number of child nodes must remain the same!")
        self._children = list(cs)

    def child(self, idx: int) -> SfgCallTreeNode:
        """Gets the child at index idx."""
        return self._children[idx]

    def set_child(self, idx: int, c: SfgCallTreeNode):
        """Replaces the child at index idx."""
        self._children[idx] = c

    def __getitem__(self, idx: int) -> SfgCallTreeNode:
        return self.child(idx)

    def __setitem__(self, idx: int, c: SfgCallTreeNode) -> None:
        self.set_child(idx, c)

    @abstractmethod
    def get_code(self, ctx: SfgContext) -> str:
        """Returns the code of this node.

        By convention, the code block emitted by this function should not contain a trailing newline.
        """

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        """Return a set of header includes required by this node"""
        return set()


class SfgCallTreeLeaf(SfgCallTreeNode, ABC):
    """A leaf node of the call tree.

    Leaf nodes must implement `required_parameters` for automatic parameter collection.
    """

    @property
    @abstractmethod
    def required_parameters(self) -> set[TypedSymbolOrObject]: ...


class SfgEmptyNode(SfgCallTreeLeaf):
    """A leaf node that does not emit any code.

    Empty nodes must still implement `required_parameters`.
    """

    def __init__(self):
        super().__init__()

    def get_code(self, ctx: SfgContext) -> str:
        return ""


class SfgStatements(SfgCallTreeLeaf):
    """Represents (a sequence of) statements in the source language.

    This class groups together arbitrary code strings
    (e.g. sequences of C++ statements, cf. https://en.cppreference.com/w/cpp/language/statements),
    and annotates them with the set of symbols read and written by these statements.

    It is the user's responsibility to ensure that the code string is valid code in the output language,
    and that the lists of required and defined objects are correct and complete.

    Args:
        code_string: Code to be printed out.
        defined_params: Objects (as `SrcObject` or `TypedSymbol`) that will be newly defined and visible to
            code in sequence after these statements.
        required_params: Objects (as `SrcObject` or `TypedSymbol`) that are required as input to these statements.
    """

    def __init__(
        self,
        code_string: str,
        defined_params: Sequence[TypedSymbolOrObject],
        required_params: Sequence[TypedSymbolOrObject],
    ):
        super().__init__()

        self._code_string = code_string

        self._defined_params = set(defined_params)
        self._required_params = set(required_params)

        self._required_includes = set()
        for obj in chain(required_params, defined_params):
            if isinstance(obj, SrcObject):
                self._required_includes |= obj.required_includes

    @property
    def required_parameters(self) -> set[TypedSymbolOrObject]:
        return self._required_params

    @property
    def defined_parameters(self) -> set[TypedSymbolOrObject]:
        return self._defined_params

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return self._required_includes

    def get_code(self, ctx: SfgContext) -> str:
        return self._code_string


class SfgFunctionParams(SfgEmptyNode):
    def __init__(self, parameters: Sequence[TypedSymbolOrObject]):
        super().__init__()
        self._params = set(parameters)

        self._required_includes = set()
        for obj in parameters:
            if isinstance(obj, SrcObject):
                self._required_includes |= obj.required_includes

    @property
    def required_parameters(self) -> set[TypedSymbolOrObject]:
        return self._params

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return self._required_includes


class SfgRequireIncludes(SfgEmptyNode):
    def __init__(self, includes: Sequence[SfgHeaderInclude]):
        super().__init__()
        self._required_includes = set(includes)

    @property
    def required_parameters(self) -> set[TypedSymbolOrObject]:
        return set()

    @property
    def required_includes(self) -> set[SfgHeaderInclude]:
        return self._required_includes


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
        subtree_code = ctx.codestyle.indent(self.subtree.get_code(ctx))

        return "{\n" + subtree_code + "\n}"


# class SfgForLoop(SfgCallTreeNode):
#     def __init__(self, control_line: SfgStatements, body: SfgCallTreeNode):
#         super().__init__(control_line, body)

#     @property
#     def body(self) -> SfgStatements:
#         return cast(SfgStatements)


class SfgKernelCallNode(SfgCallTreeLeaf):
    def __init__(self, kernel_handle: SfgKernelHandle):
        super().__init__()
        self._kernel_handle = kernel_handle

    @property
    def required_parameters(self) -> set[TypedSymbolOrObject]:
        return set(p.symbol for p in self._kernel_handle.parameters)

    def get_code(self, ctx: SfgContext) -> str:
        ast_params = self._kernel_handle.parameters
        fnc_name = self._kernel_handle.fully_qualified_name
        call_parameters = ", ".join([p.symbol.name for p in ast_params])

        return f"{fnc_name}({call_parameters});"
