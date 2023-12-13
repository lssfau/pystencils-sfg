from __future__ import annotations
from typing import TYPE_CHECKING, Sequence
from abc import ABC, abstractmethod
import numpy as np

from pystencils import Field
from pystencils.astnodes import KernelFunction

from .tree import (
    SfgCallTreeNode,
    SfgKernelCallNode,
    SfgStatements,
    SfgFunctionParams,
    SfgRequireIncludes,
    SfgSequence,
    SfgBlock,
)
from .tree.deferred_nodes import SfgDeferredFieldMapping
from .tree.conditional import SfgCondition, SfgCustomCondition, SfgBranch
from .source_components import (
    SfgFunction,
    SfgHeaderInclude,
    SfgKernelNamespace,
    SfgKernelHandle,
    SfgClass,
    SfgClassMember,
    SfgInClassDefinition,
    SfgConstructor,
    SfgMethod,
    SfgMemberVariable,
    SfgClassKeyword,
    SfgVisibility,
    SfgVisibilityBlock,
)
from .source_concepts import SrcObject, SrcField, TypedSymbolOrObject, SrcVector
from .types import cpp_typename, SrcType
from .exceptions import SfgException

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
        self._ctx.add_include(parse_include(header_file))

    def numpy_struct(
        self, name: str, dtype: np.dtype, add_constructor: bool = True
    ) -> SfgClass:
        """Add a numpy structured data type as a C++ struct

        Returns:
            The created class object
        """
        if self._ctx.get_class(name) is not None:
            raise SfgException(f"Class with name {name} already exists.")

        cls = struct_from_numpy_dtype(name, dtype, add_constructor=add_constructor)
        self._ctx.add_class(cls)
        return cls

    def kernel_function(
        self, name: str, ast_or_kernel_handle: KernelFunction | SfgKernelHandle
    ):
        """Creates a function comprising just a single kernel call.

        Args:
            ast_or_kernel_handle: Either a pystencils AST, or a kernel handle for an already registered AST.
        """
        if self._ctx.get_function(name) is not None:
            raise ValueError(f"Function {name} already exists.")

        if isinstance(ast_or_kernel_handle, KernelFunction):
            khandle = self._ctx.default_kernel_namespace.add(ast_or_kernel_handle)
            tree = SfgKernelCallNode(khandle)
        elif isinstance(ast_or_kernel_handle, SfgKernelCallNode):
            tree = ast_or_kernel_handle
        else:
            raise TypeError("Invalid type of argument `ast_or_kernel_handle`!")

        func = SfgFunction(name, tree)
        self._ctx.add_function(func)

    def function(self, name: str):
        """Add a function.

        The syntax of this function adder uses a chain of two calls to mimic C++ syntax:

        ```Python
        sfg.function("FunctionName")(
            # Function Body
        )
        ```

        The function body is constructed via sequencing;
        refer to [make_sequence][pystencilssfg.composer.make_sequence].
        """
        if self._ctx.get_function(name) is not None:
            raise ValueError(f"Function {name} already exists.")

        def sequencer(*args: str | tuple | SfgCallTreeNode | SfgNodeBuilder):
            tree = make_sequence(*args)
            func = SfgFunction(name, tree)
            self._ctx.add_function(func)

        return sequencer

    def call(self, kernel_handle: SfgKernelHandle) -> SfgKernelCallNode:
        """Use inside a function body to generate a kernel call.

        Args:
            kernel_handle: Handle to a kernel previously added to some kernel namespace.
        """
        return SfgKernelCallNode(kernel_handle)

    def seq(self, *args: SfgCallTreeNode) -> SfgSequence:
        """Syntax sequencing. For details, refer to [make_sequence][pystencilssfg.composer.make_sequence]"""
        return make_sequence(*args)

    def params(self, *args: TypedSymbolOrObject) -> SfgFunctionParams:
        """Use inside a function body to add parameters to the function."""
        return SfgFunctionParams(args)

    def require(self, *includes: str | SfgHeaderInclude) -> SfgRequireIncludes:
        return SfgRequireIncludes(list(parse_include(incl) for incl in includes))

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

    def map_param(
        self, lhs: TypedSymbolOrObject, rhs: TypedSymbolOrObject, mapping: str
    ):
        """Arbitrary parameter mapping: Add a single line of code to define a left-hand
        side object from a right-hand side."""
        return SfgStatements(mapping, (lhs,), (rhs,))

    def map_vector(self, lhs_components: Sequence[TypedSymbolOrObject], rhs: SrcVector):
        """Extracts scalar numerical values from a vector data type."""
        return make_sequence(
            *(
                rhs.extract_component(dest, coord)
                for coord, dest in enumerate(lhs_components)
            )
        )


class SfgNodeBuilder(ABC):
    @abstractmethod
    def resolve(self) -> SfgCallTreeNode:
        pass


def make_sequence(*args: tuple | str | SfgCallTreeNode | SfgNodeBuilder) -> SfgSequence:
    """Construct a sequence of C++ code from various kinds of arguments.

    `make_sequence` is ubiquitous throughout the function building front-end;
    among others, it powers the syntax of
    [SfgComposer.function][pystencilssfg.SfgComposer.function] and
    [SfgComposer.branch][pystencilssfg.SfgComposer.branch].

    `make_sequence` constructs an abstract syntax tree for code within a function body, accepting various
    types of arguments which then get turned into C++ code. These are:

     - Strings (`str`) are printed as-is
     - Tuples (`tuple`) signify *blocks*, i.e. C++ code regions enclosed in `{ }`
     - Sub-ASTs and AST builders, which are often produced by the syntactic sugar and
       factory methods of [SfgComposer][pystencilssfg.SfgComposer].

    Its usage is best shown by example:

    ```Python
    tree = make_sequence(
        "int a = 0;",
        "int b = 1;",
        (
            "int tmp = b;",
            "b = a;",
            "a = tmp;"
        ),
        SfgKernelCall(kernel_handle)
    )

    sfg.context.add_function("myFunction", tree)
    ```

    will translate to

    ```C++
    void myFunction() {
        int a = 0;
        int b = 0;
        {
            int tmp = b;
            b = a;
            a = tmp;
        }
        kernels::kernel( ... );
    }
    ```
    """
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
                    raise ValueError(
                        "Must specify exactly one argument as branch condition!"
                    )

                cond = args[0]

                if isinstance(cond, str):
                    cond = SfgCustomCondition(cond)
                elif not isinstance(cond, SfgCondition):
                    raise ValueError(
                        "Invalid type for branch condition. Must be either `str` or a subclass of `SfgCondition`."
                    )

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


def parse_include(incl: str | SfgHeaderInclude):
    if isinstance(incl, SfgHeaderInclude):
        return incl

    system_header = False
    if incl.startswith("<") and incl.endswith(">"):
        incl = incl[1:-1]
        system_header = True

    return SfgHeaderInclude(incl, system_header=system_header)


class SfgClassComposer:
    def __init__(self, ctx: SfgContext):
        self._ctx = ctx

    class VisibilityContext:
        def __init__(self, visibility: SfgVisibility):
            self._vis_block = SfgVisibilityBlock(visibility)

        def members(self):
            yield from self._vis_block.members()

        def __call__(
            self,
            *args: SfgClassMember
            | SfgClassComposer.ConstructorBuilder
            | SrcObject
            | str,
        ):
            for arg in args:
                self._vis_block.append_member(SfgClassComposer._resolve_member(arg))

            return self

        def resolve(self, cls: SfgClass) -> None:
            cls.append_visibility_block(self._vis_block)

    class ConstructorBuilder:
        def __init__(self, *params: SrcObject):
            self._params = params
            self._initializers: list[str] = []
            self._body = ""

        def init(self, initializer: str) -> SfgClassComposer.ConstructorBuilder:
            self._initializers.append(initializer)
            return self

        def body(self, body: str):
            self._body = body
            return self

        def resolve(self) -> SfgConstructor:
            return SfgConstructor(
                parameters=self._params,
                initializers=self._initializers,
                body=self._body,
            )

    def klass(self, class_name: str, bases: Sequence[str] = ()):
        return self._class(class_name, SfgClassKeyword.CLASS, bases)

    def struct(self, class_name: str, bases: Sequence[str] = ()):
        return self._class(class_name, SfgClassKeyword.STRUCT, bases)

    @property
    def public(self) -> SfgClassComposer.VisibilityContext:
        return SfgClassComposer.VisibilityContext(SfgVisibility.PUBLIC)

    @property
    def protected(self) -> SfgClassComposer.VisibilityContext:
        return SfgClassComposer.VisibilityContext(SfgVisibility.PROTECTED)

    @property
    def private(self) -> SfgClassComposer.VisibilityContext:
        return SfgClassComposer.VisibilityContext(SfgVisibility.PRIVATE)

    def var(self, name: str, dtype: SrcType):
        return SfgMemberVariable(name, dtype)

    def constructor(self, *params):
        return SfgClassComposer.ConstructorBuilder(*params)

    def method(
        self,
        name: str,
        returns: SrcType = SrcType("void"),
        inline: bool = False,
        const: bool = False,
    ):
        def sequencer(*args: str | tuple | SfgCallTreeNode | SfgNodeBuilder):
            tree = make_sequence(*args)
            return SfgMethod(
                name, tree, return_type=returns, inline=inline, const=const
            )

        return sequencer

    #   INTERNALS

    def _class(self, class_name: str, keyword: SfgClassKeyword, bases: Sequence[str]):
        if self._ctx.get_class(class_name) is not None:
            raise ValueError(f"Class or struct {class_name} already exists.")

        cls = SfgClass(class_name, class_keyword=keyword, bases=bases)
        self._ctx.add_class(cls)

        def sequencer(
            *args: SfgClassComposer.VisibilityContext
            | SfgClassMember
            | SfgClassComposer.ConstructorBuilder
            | SrcObject
            | str,
        ):
            default_ended = False

            for arg in args:
                if isinstance(arg, SfgClassComposer.VisibilityContext):
                    default_ended = True
                    arg.resolve(cls)
                elif isinstance(
                    arg,
                    (
                        SfgClassMember,
                        SfgClassComposer.ConstructorBuilder,
                        SrcObject,
                        str,
                    ),
                ):
                    if default_ended:
                        raise SfgException(
                            "Composer Syntax Error: "
                            "Cannot add members with default visibility after a visibility block."
                        )
                    else:
                        cls.default.append_member(self._resolve_member(arg))
                else:
                    raise SfgException(f"{arg} is not a valid class member.")

        return sequencer

    @staticmethod
    def _resolve_member(
        arg: SfgClassMember | SfgClassComposer.ConstructorBuilder | SrcObject | str,
    ):
        if isinstance(arg, SrcObject):
            return SfgMemberVariable(arg.name, arg.dtype)
        elif isinstance(arg, str):
            return SfgInClassDefinition(arg)
        elif isinstance(arg, SfgClassComposer.ConstructorBuilder):
            return arg.resolve()
        else:
            return arg


def struct_from_numpy_dtype(
    struct_name: str, dtype: np.dtype, add_constructor: bool = True
):
    cls = SfgClass(struct_name, class_keyword=SfgClassKeyword.STRUCT)

    fields = dtype.fields
    if fields is None:
        raise SfgException(f"Numpy dtype {dtype} is not a structured type.")

    constr_params = []
    constr_inits = []

    for member_name, type_info in fields.items():
        member_type = SrcType(cpp_typename(type_info[0]))

        member = SfgMemberVariable(member_name, member_type)

        arg = SrcObject(f"{member_name}_", member_type)

        cls.default.append_member(member)

        constr_params.append(arg)
        constr_inits.append(f"{member}({arg})")

    if add_constructor:
        cls.default.append_member(SfgConstructor(constr_params, constr_inits))

    return cls
