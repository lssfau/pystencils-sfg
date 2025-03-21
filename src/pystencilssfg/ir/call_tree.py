from __future__ import annotations
from typing import TYPE_CHECKING, Sequence, Iterable, NewType

from abc import ABC, abstractmethod

from .entities import SfgKernelHandle
from ..lang import SfgVar, HeaderFile

if TYPE_CHECKING:
    from ..config import CodeStyle


class SfgCallTreeNode(ABC):
    """Base class for all nodes comprising SFG call trees.

    ## Code Printing

    For extensibility, code printing is implemented inside the call tree.
    Therefore, every instantiable call tree node must implement the method `get_code`.
    By convention, the string returned by `get_code` should not contain a trailing newline.
    """

    def __init__(self) -> None:
        self._includes: set[HeaderFile] = set()

    @property
    @abstractmethod
    def children(self) -> Sequence[SfgCallTreeNode]:
        """This node's children"""

    @abstractmethod
    def get_code(self, cstyle: CodeStyle) -> str:
        """Returns the code of this node.

        By convention, the code block emitted by this function should not contain a trailing newline.
        """

    @property
    def depends(self) -> set[SfgVar]:
        """Set of objects this leaf depends on"""
        return set()

    @property
    def required_includes(self) -> set[HeaderFile]:
        """Return a set of header includes required by this node"""
        return self._includes


class SfgCallTreeLeaf(SfgCallTreeNode, ABC):
    """A leaf node of the call tree.

    Leaf nodes must implement ``depends`` for automatic parameter collection.
    """

    def __init__(self):
        super().__init__()

    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        return ()


class SfgEmptyNode(SfgCallTreeLeaf):
    """A leaf node that does not emit any code.

    Empty nodes must still implement ``depends``.
    """

    def __init__(self):
        super().__init__()

    def get_code(self, cstyle: CodeStyle) -> str:
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
        defined_params: Variables that will be newly defined and visible to code in sequence after these statements.
        required_params: Variables that are required as input to these statements.
    """

    def __init__(
        self,
        code_string: str,
        defines: Iterable[SfgVar],
        depends: Iterable[SfgVar],
        includes: Iterable[HeaderFile] = (),
    ):
        super().__init__()

        self._code_string = code_string

        self._defines = set(defines)
        self._depends = set(depends)
        self._includes = set(includes)

    @property
    def depends(self) -> set[SfgVar]:
        return self._depends

    @property
    def defines(self) -> set[SfgVar]:
        return self._defines

    @property
    def code_string(self) -> str:
        return self._code_string

    def get_code(self, cstyle: CodeStyle) -> str:
        return self._code_string


class SfgFunctionParams(SfgEmptyNode):
    def __init__(self, parameters: Sequence[SfgVar]):
        super().__init__()
        self._params = set(parameters)

    @property
    def depends(self) -> set[SfgVar]:
        return self._params


class SfgRequireIncludes(SfgEmptyNode):
    def __init__(self, includes: Iterable[HeaderFile]):
        super().__init__()
        self._includes = set(includes)

    @property
    def depends(self) -> set[SfgVar]:
        return set()


class SfgSequence(SfgCallTreeNode):
    __match_args__ = ("children",)

    def __init__(self, children: Sequence[SfgCallTreeNode]):
        super().__init__()
        self._children = list(children)

    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        return self._children

    @children.setter
    def children(self, cs: Sequence[SfgCallTreeNode]):
        self._children = list(cs)

    def __getitem__(self, idx: int) -> SfgCallTreeNode:
        return self._children[idx]

    def __setitem__(self, idx: int, c: SfgCallTreeNode):
        self._children[idx] = c

    def get_code(self, cstyle: CodeStyle) -> str:
        return "\n".join(c.get_code(cstyle) for c in self._children)


class SfgBlock(SfgCallTreeNode):
    def __init__(self, seq: SfgSequence):
        super().__init__()
        self._seq = seq

    @property
    def sequence(self) -> SfgSequence:
        return self._seq

    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        return (self._seq,)

    def get_code(self, cstyle: CodeStyle) -> str:
        seq_code = cstyle.indent(self._seq.get_code(cstyle))

        return "{\n" + seq_code + "\n}"


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
    def depends(self) -> set[SfgVar]:
        return set(self._kernel_handle.parameters)

    def get_code(self, cstyle: CodeStyle) -> str:
        kparams = self._kernel_handle.parameters
        fnc_name = self._kernel_handle.fqname
        call_parameters = ", ".join([p.name for p in kparams])

        return f"{fnc_name}({call_parameters});"


class SfgGpuKernelInvocation(SfgCallTreeNode):
    """A CUDA or HIP kernel invocation.

    See https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#execution-configuration
    or https://rocmdocs.amd.com/projects/HIP/en/latest/how-to/hip_cpp_language_extensions.html#calling-global-functions
    for the syntax.
    """

    def __init__(
        self,
        kernel_handle: SfgKernelHandle,
        grid_size: SfgStatements,
        block_size: SfgStatements,
        shared_memory_bytes: SfgStatements | None,
        stream: SfgStatements | None,
    ):
        from pystencils.codegen import GpuKernel

        kernel = kernel_handle.kernel
        if not isinstance(kernel, GpuKernel):
            raise ValueError(
                "An `SfgGpuKernelInvocation` node can only call GPU kernels."
            )

        super().__init__()
        self._kernel_handle = kernel_handle
        self._grid_size = grid_size
        self._block_size = block_size
        self._shared_memory_bytes = shared_memory_bytes
        self._stream = stream

    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        return (
            (
                self._grid_size,
                self._block_size,
            )
            + (
                (self._shared_memory_bytes,)
                if self._shared_memory_bytes is not None
                else ()
            )
            + ((self._stream,) if self._stream is not None else ())
        )

    @property
    def depends(self) -> set[SfgVar]:
        return set(self._kernel_handle.parameters)

    def get_code(self, cstyle: CodeStyle) -> str:
        kparams = self._kernel_handle.parameters
        fnc_name = self._kernel_handle.fqname
        call_parameters = ", ".join([p.name for p in kparams])

        grid_args = [self._grid_size, self._block_size]
        if self._shared_memory_bytes is not None:
            grid_args += [self._shared_memory_bytes]

        if self._stream is not None:
            grid_args += [self._stream]

        grid = "<<< " + ", ".join(arg.get_code(cstyle) for arg in grid_args) + " >>>"
        return f"{fnc_name}{grid}({call_parameters});"


class SfgBranch(SfgCallTreeNode):
    def __init__(
        self,
        cond: SfgStatements,
        branch_true: SfgSequence,
        branch_false: SfgSequence | None = None,
    ):
        super().__init__()
        self._cond = cond
        self._branch_true = branch_true
        self._branch_false = branch_false

    @property
    def condition(self) -> SfgStatements:
        return self._cond

    @property
    def branch_true(self) -> SfgSequence:
        return self._branch_true

    @property
    def branch_false(self) -> SfgSequence | None:
        return self._branch_false

    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        return (
            self._cond,
            self._branch_true,
        ) + ((self.branch_false,) if self.branch_false is not None else ())

    def get_code(self, cstyle: CodeStyle) -> str:
        code = f"if({self.condition.get_code(cstyle)}) {{\n"
        code += cstyle.indent(self.branch_true.get_code(cstyle))
        code += "\n}"

        if self.branch_false is not None:
            code += "else {\n"
            code += cstyle.indent(self.branch_false.get_code(cstyle))
            code += "\n}"

        return code


class SfgSwitchCase(SfgCallTreeNode):
    DefaultCaseType = NewType("DefaultCaseType", object)
    """Sentinel type representing the ``default`` case."""

    Default = DefaultCaseType(object())

    def __init__(self, label: str | SfgSwitchCase.DefaultCaseType, body: SfgSequence):
        super().__init__()
        self._label = label
        self._body = body

    @property
    def label(self) -> str | DefaultCaseType:
        return self._label

    @property
    def body(self) -> SfgSequence:
        return self._body

    @property
    def children(self) -> Sequence[SfgCallTreeNode]:
        return (self._body,)

    @property
    def is_default(self) -> bool:
        return self._label == SfgSwitchCase.Default

    def get_code(self, cstyle: CodeStyle) -> str:
        code = ""
        if self._label == SfgSwitchCase.Default:
            code += "default: {\n"
        else:
            code += f"case {self._label}: {{\n"
        code += cstyle.indent(self.body.get_code(cstyle))
        code += "\n}"
        return code


class SfgSwitch(SfgCallTreeNode):
    def __init__(
        self,
        switch_arg: SfgStatements,
        cases_dict: dict[str, SfgSequence],
        default: SfgSequence | None = None,
    ):
        super().__init__()
        self._cases = [SfgSwitchCase(label, body) for label, body in cases_dict.items()]
        if default is not None:
            # invariant: the default case is always the last child
            self._cases += [SfgSwitchCase(SfgSwitchCase.Default, default)]
        self._switch_arg = switch_arg
        self._default = (
            SfgSwitchCase(SfgSwitchCase.Default, default)
            if default is not None
            else None
        )

    @property
    def switch_arg(self) -> str | SfgStatements:
        return self._switch_arg

    @property
    def default(self) -> SfgCallTreeNode | None:
        return self._default

    @property
    def children(self) -> tuple[SfgCallTreeNode, ...]:
        return (self._switch_arg,) + tuple(self._cases)

    @property
    def cases(self) -> tuple[SfgCallTreeNode, ...]:
        if self._default is not None:
            return tuple(self._cases[:-1])
        else:
            return tuple(self._cases)

    @cases.setter
    def cases(self, cs: Sequence[SfgSwitchCase]) -> None:
        if len(cs) != len(self._cases):
            raise ValueError("The number of child nodes must remain the same!")

        self._default = None
        for i, c in enumerate(cs):
            if c.is_default:
                if i != len(cs) - 1:
                    raise ValueError("Default case must be listed last.")
                else:
                    self._default = c

        self._children = list(cs)

    def set_case(self, idx: int, c: SfgSwitchCase):
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

    def get_code(self, cstyle: CodeStyle) -> str:
        code = f"switch({self._switch_arg.get_code(cstyle)}) {{\n"
        code += "\n".join(c.get_code(cstyle) for c in self._cases)
        code += "}"
        return code
