from __future__ import annotations
from typing import TYPE_CHECKING, Sequence
from abc import ABC, abstractmethod

from pystencils import Field
from pystencils.astnodes import KernelFunction

from .tree import SfgCallTreeNode, SfgKernelCallNode, SfgStatements, SfgSequence, SfgBlock
from .tree.deferred_nodes import SfgDeferredFieldMapping
from .tree.conditional import SfgCondition, SfgCustomCondition, SfgBranch
from .source_components import SfgFunction, SfgHeaderInclude, SfgKernelNamespace, SfgKernelHandle
from .source_concepts import SrcField, TypedSymbolOrObject, SrcVector

if TYPE_CHECKING:
    from .context import SfgContext


class SfgComposer:
    """Primary interface for constructing source files in pystencils-sfg."""

    def __init__(self, ctx: SfgContext):
        self._ctx = ctx

    @property
    def context(self):
        return self._ctx

    def prelude(self, content: str):
        """Add a string to the code file's prelude.

        Do not wrap the given string in comment syntax."""
        self._ctx.append_to_prelude(content)

    def define(self, definition: str):
        """Add a custom definition to the generated header file."""
        self._ctx.add_definition(definition)

    def namespace(self, namespace: str):
        """Set the inner code namespace. Throws an exception if a namespace was already set."""
        self._ctx.set_namespace(namespace)

    @property
    def kernels(self) -> SfgKernelNamespace:
        """The default kernel namespace. Add kernels like:
        ```Python
        sfg.kernels.add(ast, "kernel_name")
        sfg.kernels.create(assignments, "kernel_name", config)
        ```"""
        return self._ctx._default_kernel_namespace

    def kernel_namespace(self, name: str) -> SfgKernelNamespace:
        """Returns the kernel namespace of the given name, creating it if it does not exist yet."""
        kns = self._ctx.get_kernel_namespace(name)
        if kns is None:
            kns = SfgKernelNamespace(self, name)
            self._ctx.add_kernel_namespace(kns)

        return kns

    def include(self, header_file: str):
        system_header = False
        if header_file.startswith("<") and header_file.endswith(">"):
            header_file = header_file[1:-1]
            system_header = True

        self._ctx.add_include(SfgHeaderInclude(header_file, system_header=system_header))

    def kernel_function(self, name: str, ast_or_kernel_handle: KernelFunction | SfgKernelHandle):
        if self._ctx.get_function(name) is not None:
            raise ValueError(f"Function {name} already exists.")

        if isinstance(ast_or_kernel_handle, KernelFunction):
            khandle = self._ctx.default_kernel_namespace.add(ast_or_kernel_handle)
            tree = SfgKernelCallNode(khandle)
        elif isinstance(ast_or_kernel_handle, SfgKernelCallNode):
            tree = ast_or_kernel_handle
        else:
            raise TypeError("Invalid type of argument `ast_or_kernel_handle`!")

        func = SfgFunction(self._ctx, name, tree)
        self._ctx.add_function(func)

    def function(self, name: str):
        """Add a function.

        The syntax of this function adder uses a chain of two calls to mimic C++ syntax:

        ```Python
        sfg.function("FunctionName")(
            # Function Body
        )
        ```
        """
        if self._ctx.get_function(name) is not None:
            raise ValueError(f"Function {name} already exists.")

        def sequencer(*args: str | tuple | SfgCallTreeNode | SfgNodeBuilder):
            tree = make_sequence(*args)
            func = SfgFunction(self._ctx, name, tree)
            self._ctx.add_function(func)

        return sequencer

    def call(self, kernel_handle: SfgKernelHandle) -> SfgKernelCallNode:
        """Use inside a function body to generate a kernel call.

        Args:
            kernel_handle: Handle to a kernel previously added to some kernel namespace.
        """
        return SfgKernelCallNode(kernel_handle)

    def seq(self, *args: SfgCallTreeNode) -> SfgSequence:
        return make_sequence(*args)

    @property
    def branch(self) -> SfgBranchBuilder:
        """Use inside a function body to create an if/else conditonal branch.

        The syntax is:
        ```Python
        sfg.branch("condition")(
            # then-body
        )(
            # else-body (may be omitted)
        )
        ```
        """
        return SfgBranchBuilder()

    def map_field(self, field: Field, src_object: SrcField) -> SfgDeferredFieldMapping:
        """Map a pystencils field to a field data structure, from which pointers, sizes
        and strides should be extracted.

        Args:
            field: The pystencils field to be mapped
            src_object: A `SrcField` object representing a field data structure.
        """
        return SfgDeferredFieldMapping(field, src_object)

    def map_param(self, lhs: TypedSymbolOrObject, rhs: TypedSymbolOrObject, mapping: str):
        """Arbitrary parameter mapping: Add a single line of code to define a left-hand
        side object from a right-hand side."""
        return SfgStatements(mapping, (lhs,), (rhs,))

    def map_vector(self, lhs_components: Sequence[TypedSymbolOrObject], rhs: SrcVector):
        """Extracts scalar numerical values from a vector data type."""
        return make_sequence(*(
            rhs.extract_component(dest, coord) for coord, dest in enumerate(lhs_components)
        ))


class SfgNodeBuilder(ABC):
    @abstractmethod
    def resolve(self) -> SfgCallTreeNode:
        pass


def make_sequence(*args: tuple | str | SfgCallTreeNode | SfgNodeBuilder) -> SfgSequence:
    children = []
    for i, arg in enumerate(args):
        if isinstance(arg, SfgNodeBuilder):
            children.append(arg.resolve())
        elif isinstance(arg, SfgCallTreeNode):
            children.append(arg)
        elif isinstance(arg, str):
            children.append(SfgStatements(arg, (), ()))
        elif isinstance(arg, tuple):
            #   Tuples are treated as blocks
            subseq = make_sequence(*arg)
            children.append(SfgBlock(subseq))
        else:
            raise TypeError(f"Sequence argument {i} has invalid type.")

    return SfgSequence(children)


class SfgBranchBuilder(SfgNodeBuilder):
    def __init__(self):
        self._phase = 0

        self._cond = None
        self._branch_true = SfgSequence(())
        self._branch_false = None

    def __call__(self, *args) -> SfgBranchBuilder:
        match self._phase:
            case 0:  # Condition
                if len(args) != 1:
                    raise ValueError("Must specify exactly one argument as branch condition!")

                cond = args[0]

                if isinstance(cond, str):
                    cond = SfgCustomCondition(cond)
                elif not isinstance(cond, SfgCondition):
                    raise ValueError(
                        "Invalid type for branch condition. Must be either `str` or a subclass of `SfgCondition`.")

                self._cond = cond

            case 1:  # Then-branch
                self._branch_true = make_sequence(*args)
            case 2:  # Else-branch
                self._branch_false = make_sequence(*args)
            case _:  # There's no third branch!
                raise TypeError("Branch construct already complete.")

        self._phase += 1

        return self

    def resolve(self) -> SfgCallTreeNode:
        assert self._cond is not None
        return SfgBranch(self._cond, self._branch_true, self._branch_false)
