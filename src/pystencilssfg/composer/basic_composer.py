from __future__ import annotations
from typing import Sequence
from abc import ABC, abstractmethod
import numpy as np
import sympy as sp
from functools import reduce

from pystencils import Field
from pystencils.backend import KernelParameter, KernelFunction
from pystencils.types import create_type, UserTypeSpec, PsCustomType, PsPointerType

from ..context import SfgContext
from .custom import CustomGenerator
from ..ir import (
    SfgCallTreeNode,
    SfgKernelCallNode,
    SfgCudaKernelInvocation,
    SfgStatements,
    SfgFunctionParams,
    SfgRequireIncludes,
    SfgSequence,
    SfgBlock,
    SfgBranch,
    SfgSwitch,
)
from ..ir.postprocessing import (
    SfgDeferredParamMapping,
    SfgDeferredFieldMapping,
    SfgDeferredVectorMapping,
)
from ..ir.source_components import (
    SfgFunction,
    SfgHeaderInclude,
    SfgKernelNamespace,
    SfgKernelHandle,
    SfgClass,
    SfgConstructor,
    SfgMemberVariable,
    SfgClassKeyword,
    SfgVar,
)
from ..lang import IFieldExtraction, SrcVector, AugExpr, SrcField
from ..exceptions import SfgException


class SfgIComposer(ABC):
    def __init__(self, ctx: SfgContext):
        self._ctx = ctx

    @property
    def context(self):
        return self._ctx


class SfgNodeBuilder(ABC):
    @abstractmethod
    def resolve(self) -> SfgCallTreeNode:
        pass


ExprLike = str | SfgVar | AugExpr
SequencerArg = tuple | str | AugExpr | SfgCallTreeNode | SfgNodeBuilder


class SfgBasicComposer(SfgIComposer):
    """Composer for basic source components, and base class for all composer mix-ins."""

    def __init__(self, sfg: SfgContext | SfgIComposer):
        ctx: SfgContext = sfg if isinstance(sfg, SfgContext) else sfg.context
        super().__init__(ctx)

    def prelude(self, content: str):
        """Append a string to the prelude comment, to be printed at the top of both generated files.

        The string should not contain C/C++ comment delimiters, since these will be added automatically
        during code generation.
        """
        self._ctx.append_to_prelude(content)

    def define(self, *definitions: str):
        """Add custom definitions to the generated header file."""
        for d in definitions:
            self._ctx.add_definition(d)

    def define_once(self, *definitions: str):
        """Same as `define`, but only adds definitions only if the same code string was not already added."""
        for definition in definitions:
            if all(d != definition for d in self._ctx.definitions()):
                self._ctx.add_definition(definition)

    def namespace(self, namespace: str):
        """Set the inner code namespace. Throws an exception if a namespace was already set."""
        self._ctx.set_namespace(namespace)

    def generate(self, generator: CustomGenerator):
        """Invoke a custom code generator with the underlying context."""
        generator.generate(self._ctx)

    @property
    def kernels(self) -> SfgKernelNamespace:
        """The default kernel namespace.

        Add kernels like::

            sfg.kernels.add(ast, "kernel_name")
            sfg.kernels.create(assignments, "kernel_name", config)
        """
        return self._ctx._default_kernel_namespace

    def kernel_namespace(self, name: str) -> SfgKernelNamespace:
        """Return the kernel namespace of the given name, creating it if it does not exist yet."""
        kns = self._ctx.get_kernel_namespace(name)
        if kns is None:
            kns = SfgKernelNamespace(self._ctx, name)
            self._ctx.add_kernel_namespace(kns)

        return kns

    def include(self, header_file: str, private: bool = False):
        """Include a header file.

        Args:
            header_file: Path to the header file. Enclose in `<>` for a system header.
            private: If `True`, in header-implementation code generation, the header file is
                only included in the implementation file.
        """
        self._ctx.add_include(SfgHeaderInclude.parse(header_file, private))

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
        """Create a function comprising just a single kernel call.

        Args:
            ast_or_kernel_handle: Either a pystencils AST, or a kernel handle for an already registered AST.
        """
        if self._ctx.get_function(name) is not None:
            raise ValueError(f"Function {name} already exists.")

        if isinstance(ast_or_kernel_handle, KernelFunction):
            khandle = self._ctx.default_kernel_namespace.add(ast_or_kernel_handle)
            tree = SfgKernelCallNode(khandle)
        elif isinstance(ast_or_kernel_handle, SfgKernelHandle):
            tree = SfgKernelCallNode(ast_or_kernel_handle)
        else:
            raise TypeError("Invalid type of argument `ast_or_kernel_handle`!")

        func = SfgFunction(name, tree)
        self._ctx.add_function(func)

    def function(self, name: str):
        """Add a function.

        The syntax of this function adder uses a chain of two calls to mimic C++ syntax:

        .. code-block:: Python

            sfg.function("FunctionName")(
                # Function Body
            )

        The function body is constructed via sequencing (see `make_sequence`).
        """
        if self._ctx.get_function(name) is not None:
            raise ValueError(f"Function {name} already exists.")

        def sequencer(*args: str | tuple | SfgCallTreeNode | SfgNodeBuilder):
            tree = make_sequence(*args)
            func = SfgFunction(name, tree)
            self._ctx.add_function(func)

        return sequencer

    def call(self, kernel_handle: SfgKernelHandle) -> SfgCallTreeNode:
        """Use inside a function body to directly call a kernel.

        When using `call`, the given kernel will simply be called as a function.
        To invoke a GPU kernel on a specified launch grid, use `cuda_invoke`
        or the interfaces of `pystencilssfg.extensions.sycl` instead.

        Args:
            kernel_handle: Handle to a kernel previously added to some kernel namespace.
        """
        return SfgKernelCallNode(kernel_handle)

    def cuda_invoke(
        self,
        kernel_handle: SfgKernelHandle,
        num_blocks: ExprLike,
        threads_per_block: ExprLike,
        stream: ExprLike | None,
    ):
        num_blocks_str = str(num_blocks)
        tpb_str = str(threads_per_block)
        stream_str = str(stream) if stream is not None else None
        depends = _depends(num_blocks) | _depends(threads_per_block) | _depends(stream)
        return SfgCudaKernelInvocation(
            kernel_handle, num_blocks_str, tpb_str, stream_str, depends
        )

    def seq(self, *args: tuple | str | SfgCallTreeNode | SfgNodeBuilder) -> SfgSequence:
        """Syntax sequencing. For details, see `make_sequence`"""
        return make_sequence(*args)

    def params(self, *args: SfgVar) -> SfgFunctionParams:
        """Use inside a function body to add parameters to the function."""
        return SfgFunctionParams(args)

    def require(self, *includes: str | SfgHeaderInclude) -> SfgRequireIncludes:
        return SfgRequireIncludes(
            list(SfgHeaderInclude.parse(incl) for incl in includes)
        )

    def cpptype(
        self,
        typename: UserTypeSpec,
        ptr: bool = False,
        ref: bool = False,
        const: bool = False,
    ):
        if ptr and ref:
            raise SfgException("Create either a pointer, or a ref type, not both!")

        ref_qual = "&" if ref else ""
        try:
            base_type = create_type(typename)
        except ValueError:
            if not isinstance(typename, str):
                raise ValueError(f"Could not parse type: {typename}")

            base_type = PsCustomType(typename + ref_qual, const=const)

        if ptr:
            return PsPointerType(base_type)
        else:
            return base_type

    def var(self, name: str, dtype: UserTypeSpec) -> SfgVar:
        """Create a variable with given name and data type."""
        return SfgVar(name, create_type(dtype))

    def init(self, lhs: SfgVar) -> SfgInplaceInitBuilder:
        """Create a C++ in-place initialization.

        Usage:

        .. code-block:: Python

            obj = sfg.var("obj", "SomeClass")
            sfg.init(obj)(arg1, arg2, arg3)

        becomes

        .. code-block:: C++

            SomeClass obj { arg1, arg2, arg3 };
        """
        return SfgInplaceInitBuilder(lhs)

    def expr(self, fmt: str, *deps, **kwdeps):
        return AugExpr.format(fmt, *deps, **kwdeps)

    @property
    def branch(self) -> SfgBranchBuilder:
        """Use inside a function body to create an if/else conditonal branch.

        The syntax is:

        .. code-block:: Python

            sfg.branch("condition")(
                # then-body
            )(
                # else-body (may be omitted)
            )
        """
        return SfgBranchBuilder()

    def switch(self, switch_arg: ExprLike) -> SfgSwitchBuilder:
        return SfgSwitchBuilder(switch_arg)

    def map_field(
        self, field: Field, index_provider: IFieldExtraction | SrcField
    ) -> SfgDeferredFieldMapping:
        """Map a pystencils field to a field data structure, from which pointers, sizes
        and strides should be extracted.

        Args:
            field: The pystencils field to be mapped
            src_object: A `IFieldIndexingProvider` object representing a field data structure.
        """
        return SfgDeferredFieldMapping(field, index_provider)

    def map_param(
        self,
        lhs: SfgVar,
        rhs: SfgVar | Sequence[SfgVar],
        mapping: str,
    ):
        """Arbitrary parameter mapping: Add a single line of code to define a left-hand
        side object from one or multiple right-hand side dependencies."""
        if isinstance(rhs, (KernelParameter, SfgVar)):
            rhs = [rhs]
        return SfgDeferredParamMapping(lhs, set(rhs), mapping)

    def map_vector(self, lhs_components: Sequence[SfgVar | sp.Symbol], rhs: SrcVector):
        """Extracts scalar numerical values from a vector data type.

        Args:
            lhs_components: Vector components as a list of symbols.
            rhs: A `SrcVector` object representing a vector data structure.
        """
        return SfgDeferredVectorMapping(lhs_components, rhs)


def make_statements(arg: ExprLike) -> SfgStatements:
    match arg:
        case str():
            return SfgStatements(arg, (), ())
        case SfgVar(name, _):
            return SfgStatements(name, (), (arg,))
        case AugExpr():
            return SfgStatements(str(arg), (), arg.depends)
        case _:
            assert False


def make_sequence(*args: SequencerArg) -> SfgSequence:
    """Construct a sequence of C++ code from various kinds of arguments.

    `make_sequence` is ubiquitous throughout the function building front-end;
    among others, it powers the syntax of `SfgComposer.function` and `SfgComposer.branch`.

    `make_sequence` constructs an abstract syntax tree for code within a function body, accepting various
    types of arguments which then get turned into C++ code. These are

    - Strings (`str`) are printed as-is
    - Tuples (`tuple`) signify *blocks*, i.e. C++ code regions enclosed in ``{ }``
    - Sub-ASTs and AST builders, which are often produced by the syntactic sugar and
      factory methods of `SfgComposer`.

    Its usage is best shown by example:

    .. code-block:: Python

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

    will translate to

    .. code-block:: C++

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
    """
    children = []
    for i, arg in enumerate(args):
        if isinstance(arg, SfgNodeBuilder):
            children.append(arg.resolve())
        elif isinstance(arg, SfgCallTreeNode):
            children.append(arg)
        elif isinstance(arg, AugExpr):
            children.append(SfgStatements(str(arg), (), arg.depends))
        elif isinstance(arg, str):
            children.append(SfgStatements(arg, (), ()))
        elif isinstance(arg, tuple):
            #   Tuples are treated as blocks
            subseq = make_sequence(*arg)
            children.append(SfgBlock(subseq))
        else:
            raise TypeError(f"Sequence argument {i} has invalid type.")

    return SfgSequence(children)


class SfgInplaceInitBuilder(SfgNodeBuilder):
    def __init__(self, lhs: SfgVar) -> None:
        self._lhs: SfgVar = lhs
        self._depends: set[SfgVar] = set()
        self._rhs: str | None = None

    def __call__(
        self,
        *rhs: str | AugExpr,
    ) -> SfgInplaceInitBuilder:
        if self._rhs is not None:
            raise SfgException("Assignment builder used multiple times.")

        self._rhs = ", ".join(str(expr) for expr in rhs)
        self._depends = reduce(
            set.union, (obj.depends for obj in rhs if isinstance(obj, AugExpr)), set()
        )
        return self

    def resolve(self) -> SfgCallTreeNode:
        assert self._rhs is not None
        return SfgStatements(
            f"{self._lhs.dtype} {self._lhs.name} {{ {self._rhs} }};",
            [self._lhs],
            self._depends,
        )


class SfgBranchBuilder(SfgNodeBuilder):
    def __init__(self) -> None:
        self._phase = 0

        self._cond: ExprLike | None = None
        self._branch_true = SfgSequence(())
        self._branch_false: SfgSequence | None = None

    def __call__(self, *args) -> SfgBranchBuilder:
        match self._phase:
            case 0:  # Condition
                if len(args) != 1:
                    raise ValueError(
                        "Must specify exactly one argument as branch condition!"
                    )

                self._cond = args[0]

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
        return SfgBranch(
            make_statements(self._cond), self._branch_true, self._branch_false
        )


class SfgSwitchBuilder(SfgNodeBuilder):
    def __init__(self, switch_arg: ExprLike):
        self._switch_arg = switch_arg
        self._cases: dict[str, SfgSequence] = dict()
        self._default: SfgSequence | None = None

    def case(self, label: str):
        if label in self._cases:
            raise SfgException(f"Duplicate case: {label}")

        def sequencer(*args: SequencerArg):
            tree = make_sequence(*args)
            self._cases[label] = tree
            return self

        return sequencer

    def cases(self, cases_dict: dict[str, SequencerArg]):
        for key, value in cases_dict.items():
            self.case(key)(value)
        return self

    def default(self, *args):
        if self._default is not None:
            raise SfgException("Duplicate default case")

        tree = make_sequence(*args)
        self._default = tree

        return self

    def resolve(self) -> SfgCallTreeNode:
        return SfgSwitch(make_statements(self._switch_arg), self._cases, self._default)


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
        member_type = create_type(type_info[0])

        member = SfgMemberVariable(member_name, member_type)

        arg = SfgVar(f"{member_name}_", member_type)

        cls.default.append_member(member)

        constr_params.append(arg)
        constr_inits.append(f"{member}({arg})")

    if add_constructor:
        cls.default.append_member(SfgConstructor(constr_params, constr_inits))

    return cls


def _depends(expr: ExprLike | Sequence[ExprLike] | None) -> set[SfgVar]:
    match expr:
        case None | str():
            return set()
        case SfgVar():
            return {expr}
        case AugExpr():
            return expr.depends
        case _:
            raise ValueError(f"Invalid expression: {expr}")
