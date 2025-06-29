from __future__ import annotations

from typing import Sequence, TypeAlias
from abc import ABC, abstractmethod
import sympy as sp
from functools import reduce
from warnings import warn

from pystencils import (
    Field,
    CreateKernelConfig,
    create_kernel,
    Assignment,
    AssignmentCollection,
)
from pystencils.codegen import Kernel, Lambda
from pystencils.types import create_type, UserTypeSpec, PsType

from ..context import SfgContext, SfgCursor
from .custom import CustomGenerator
from ..ir import (
    SfgCallTreeNode,
    SfgKernelCallNode,
    SfgStatements,
    SfgFunctionParams,
    SfgRequireIncludes,
    SfgSequence,
    SfgBlock,
    SfgBranch,
    SfgSwitch,
)
from ..ir.postprocessing import (
    SfgDeferredParamSetter,
    SfgDeferredFieldMapping,
    SfgDeferredVectorMapping,
)
from ..ir import (
    SfgFunction,
    SfgKernelNamespace,
    SfgKernelHandle,
    SfgEntityDecl,
    SfgEntityDef,
    SfgNamespaceBlock,
)
from ..lang import (
    VarLike,
    ExprLike,
    _VarLike,
    _ExprLike,
    asvar,
    depends,
    HeaderFile,
    includes,
    SfgVar,
    SfgKernelParamVar,
    AugExpr,
    SupportsFieldExtraction,
    SupportsVectorExtraction,
    void,
)
from ..exceptions import SfgException


class SfgIComposer(ABC):
    def __init__(self, ctx: SfgContext):
        self._ctx = ctx
        self._cursor = ctx.cursor

    @property
    def context(self):
        return self._ctx


class SfgNodeBuilder(ABC):
    """Base class for node builders used by the composer"""

    @abstractmethod
    def resolve(self) -> SfgCallTreeNode:
        pass


_SequencerArg = (tuple, ExprLike, SfgCallTreeNode, SfgNodeBuilder)
SequencerArg: TypeAlias = tuple | ExprLike | SfgCallTreeNode | SfgNodeBuilder
"""Valid arguments to `make_sequence` and any sequencer that uses it."""


class KernelsAdder:
    """Handle on a kernel namespace that permits registering kernels."""

    def __init__(self, cursor: SfgCursor, knamespace: SfgKernelNamespace):
        self._cursor = cursor
        self._kernel_namespace = knamespace
        self._inline: bool = False
        self._loc: SfgNamespaceBlock | None = None

    def inline(self) -> KernelsAdder:
        """Generate kernel definitions ``inline`` in the header file."""
        self._inline = True
        return self

    def add(self, kernel: Kernel, name: str | None = None):
        """Adds an existing pystencils AST to this namespace.
        If a name is specified, the AST's function name is changed."""
        if name is None:
            kernel_name = kernel.name
        else:
            kernel_name = name

        if self._kernel_namespace.find_kernel(kernel_name) is not None:
            raise ValueError(
                f"Duplicate kernels: A kernel called {kernel_name} already exists "
                f"in namespace {self._kernel_namespace.fqname}"
            )

        if name is not None:
            kernel.name = kernel_name

        khandle = SfgKernelHandle(
            kernel_name, self._kernel_namespace, kernel, inline=self._inline
        )
        self._kernel_namespace.add_kernel(khandle)

        loc = self._get_loc()
        loc.elements.append(SfgEntityDef(khandle))

        for header in kernel.required_headers:
            hfile = HeaderFile.parse(header)
            if self._inline:
                self._cursor.context.header_file.includes.append(hfile)
            else:
                impl_file = self._cursor.context.impl_file
                assert impl_file is not None
                impl_file.includes.append(hfile)

        return khandle

    def create(
        self,
        assignments: Assignment | Sequence[Assignment] | AssignmentCollection,
        name: str | None = None,
        config: CreateKernelConfig | None = None,
    ):
        """Creates a new pystencils kernel from a list of assignments and a configuration.
        This is a wrapper around `create_kernel <pystencils.codegen.create_kernel>`
        with a subsequent call to `add`.
        """
        if config is None:
            config = CreateKernelConfig()

        if name is not None:
            if self._kernel_namespace.find_kernel(name) is not None:
                raise ValueError(
                    f"Duplicate kernels: A kernel called {name} already exists "
                    f"in namespace {self._kernel_namespace.fqname}"
                )

            config.function_name = name

        kernel = create_kernel(assignments, config=config)
        return self.add(kernel)

    def _get_loc(self) -> SfgNamespaceBlock:
        if self._loc is None:
            kns_block = SfgNamespaceBlock(self._kernel_namespace)

            if self._inline:
                self._cursor.write_header(kns_block)
            else:
                self._cursor.write_impl(kns_block)

            self._loc = kns_block
        return self._loc


class SfgBasicComposer(SfgIComposer):
    """Composer for basic source components, and base class for all composer mix-ins."""

    def __init__(self, sfg: SfgContext | SfgIComposer):
        ctx: SfgContext = sfg if isinstance(sfg, SfgContext) else sfg.context
        super().__init__(ctx)

    def prelude(self, content: str, end: str = "\n"):
        """Append a string to the prelude comment, to be printed at the top of both generated files.

        The string should not contain C/C++ comment delimiters, since these will be added automatically
        during code generation.

        :Example:
            >>> sfg.prelude("This file was generated using pystencils-sfg; do not modify it directly!")

            will appear in the generated files as

            .. code-block:: C++

                /*
                 * This file was generated using pystencils-sfg; do not modify it directly!
                 */

        """
        for f in self._ctx.files:
            if f.prelude is None:
                f.prelude = content + end
            else:
                f.prelude += content + end

    def code(self, *code: str, impl: bool = False):
        """Add arbitrary lines of code to the generated header file.

        :Example:

            >>> sfg.code(
            ...     "#define PI 3.14  // more than enough for engineers",
            ...     "using namespace std;"
            ... )

            will appear as

            .. code-block:: C++

                #define PI 3.14 // more than enough for engineers
                using namespace std;

        Args:
            code: Sequence of code strings to be written to the output file
            impl: If `True`, write the code to the implementation file; otherwise, to the header file.
        """
        for c in code:
            if impl:
                self._cursor.write_impl(c)
            else:
                self._cursor.write_header(c)

    def define(self, *definitions: str):
        from warnings import warn

        warn(
            "The `define` method of `SfgBasicComposer` is deprecated and will be removed in a future version."
            "Use `sfg.code()` instead.",
            FutureWarning,
        )

        self.code(*definitions)

    def namespace(self, namespace: str):
        """Enter a new namespace block.

        Calling `namespace` as a regular function will open a new namespace as a child of the
        currently active namespace; this new namespace will then become active instead.
        Using `namespace` as a context manager will instead activate the given namespace
        only for the length of the ``with`` block.

        Args:
            namespace: Qualified name of the namespace

        :Example:

        The following calls will set the current namespace to ``outer::inner``
        for the remaining code generation run:

        .. code-block::

            sfg.namespace("outer")
            sfg.namespace("inner")

        Subsequent calls to `namespace` can only create further nested namespaces.

        To step back out of a namespace, `namespace` can also be used as a context manager:

        .. code-block::

            with sfg.namespace("detail"):
                ...

        This way, code generated inside the ``with`` region is placed in the ``detail`` namespace,
        and code after this block will again live in the enclosing namespace.

        """
        return self._cursor.enter_namespace(namespace)

    def generate(self, generator: CustomGenerator):
        """Invoke a custom code generator with the underlying context."""
        from .composer import SfgComposer

        generator.generate(SfgComposer(self))

    @property
    def kernels(self) -> KernelsAdder:
        """The default kernel namespace.

        Add kernels like::

            sfg.kernels.add(ast, "kernel_name")
            sfg.kernels.create(assignments, "kernel_name", config)
        """
        return self.kernel_namespace("kernels")

    def kernel_namespace(self, name: str) -> KernelsAdder:
        """Return a view on a kernel namespace in order to add kernels to it."""
        kns = self._cursor.get_entity(name)
        if kns is None:
            kns = SfgKernelNamespace(name, self._cursor.current_namespace)
            self._cursor.add_entity(kns)
        elif not isinstance(kns, SfgKernelNamespace):
            raise ValueError(
                f"The existing entity {kns.fqname} is not a kernel namespace"
            )

        kadder = KernelsAdder(self._cursor, kns)
        if self._ctx.impl_file is None:
            kadder.inline()
        return kadder

    def include(self, header: str | HeaderFile, private: bool = False):
        """Include a header file.

        Args:
            header_file: Path to the header file. Enclose in ``<>`` for a system header.
            private: If ``True``, in header-implementation code generation, the header file is
                only included in the implementation file.

        :Example:

            >>> sfg.include("<vector>")
            >>> sfg.include("custom.h")

            will be printed as

            .. code-block:: C++

                #include <vector>
                #include "custom.h"
        """
        header_file = HeaderFile.parse(header)

        if private:
            if self._ctx.impl_file is None:
                raise ValueError(
                    "Cannot emit a private include since no implementation file is being generated"
                )
            self._ctx.impl_file.includes.append(header_file)
        else:
            self._ctx.header_file.includes.append(header_file)

    def kernel_function(self, name: str, kernel: Kernel | SfgKernelHandle):
        """Create a function comprising just a single kernel call.

        Args:
            ast_or_kernel_handle: Either a pystencils AST, or a kernel handle for an already registered AST.
        """
        if isinstance(kernel, Kernel):
            khandle = self.kernels.add(kernel, name)
        else:
            khandle = kernel

        self.function(name)(self.call(khandle))

    def function(
        self,
        name: str,
        return_type: UserTypeSpec | None = None,
    ) -> SfgFunctionSequencer:
        """Add a function.

        The syntax of this function adder uses a chain of two calls to mimic C++ syntax:

        .. code-block:: Python

            sfg.function("FunctionName")(
                # Function Body
            )

        The function body is constructed via sequencing (see `make_sequence`).
        """
        seq = SfgFunctionSequencer(self._cursor, name)

        if return_type is not None:
            warn(
                "The parameter `return_type` to `function()` is deprecated and will be removed by version 0.1. "
                "Use `.returns()` instead.",
                FutureWarning,
            )
            seq.returns(return_type)

        if self._ctx.impl_file is None:
            seq.inline()

        return seq

    def call(self, kernel_handle: SfgKernelHandle) -> SfgCallTreeNode:
        """Use inside a function body to directly call a kernel.

        When using `call`, the given kernel will simply be called as a function.
        To invoke a GPU kernel on a specified launch grid,
        use `gpu_invoke <SfgGpuComposer.gpu_invoke>` instead.

        Args:
            kernel_handle: Handle to a kernel previously added to some kernel namespace.
        """
        return SfgKernelCallNode(kernel_handle)

    def seq(self, *args: tuple | str | SfgCallTreeNode | SfgNodeBuilder) -> SfgSequence:
        """Syntax sequencing. For details, see `make_sequence`"""
        return make_sequence(*args)

    def params(self, *args: AugExpr) -> SfgFunctionParams:
        """Use inside a function body to add parameters to the function."""
        return SfgFunctionParams([x.as_variable() for x in args])

    def require(self, *incls: str | HeaderFile) -> SfgRequireIncludes:
        """Use inside a function body to require the inclusion of headers."""
        return SfgRequireIncludes((HeaderFile.parse(incl) for incl in incls))

    def var(self, name: str, dtype: UserTypeSpec) -> AugExpr:
        """Create a variable with given name and data type."""
        return AugExpr(create_type(dtype)).var(name)

    def vars(self, names: str, dtype: UserTypeSpec) -> tuple[AugExpr, ...]:
        """Create multiple variables with given names and the same data type.

        Example:

        >>> sfg.vars("x, y, z", "float32")
        (x, y, z)

        """
        varnames = names.split(",")
        return tuple(self.var(n.strip(), dtype) for n in varnames)

    def init(self, lhs: VarLike):
        """Create a C++ in-place initialization.

        Usage:

        .. code-block:: Python

            obj = sfg.var("obj", "SomeClass")
            sfg.init(obj)(arg1, arg2, arg3)

        becomes

        .. code-block:: C++

            SomeClass obj { arg1, arg2, arg3 };
        """
        lhs_var = asvar(lhs)

        def parse_args(*args: ExprLike):
            args_str = ", ".join(str(arg) for arg in args)
            deps: set[SfgVar] = reduce(set.union, (depends(arg) for arg in args), set())
            incls: set[HeaderFile] = reduce(set.union, (includes(arg) for arg in args))
            return SfgStatements(
                f"{lhs_var.dtype.c_string()} {lhs_var.name} {{ {args_str} }};",
                (lhs_var,),
                deps,
                incls,
            )

        return parse_args

    def expr(self, fmt: str, *deps, **kwdeps) -> AugExpr:
        """Create an expression while keeping track of variables it depends on.

        This method is meant to be used similarly to `str.format`; in fact,
        it calls `str.format` internally and therefore supports all of its
        formatting features.
        In addition, however, the format arguments are scanned for *variables*
        (e.g. created using `var`), which are attached to the expression.
        This way, *pystencils-sfg* keeps track of any variables an expression depends on.

        :Example:

            >>> x, y, z, w = sfg.vars("x, y, z, w", "float32")
            >>> expr = sfg.expr("{} + {} * {}", x, y, z)
            >>> expr
            x + y * z

            You can look at the expression's dependencies:

            >>> sorted(expr.depends, key=lambda v: v.name)
            [x: float32, y: float32, z: float32]

            If you use an existing expression to create a larger one, the new expression
            inherits all variables from its parts:

            >>> expr2 = sfg.expr("{} + {}", expr, w)
            >>> expr2
            x + y * z + w
            >>> sorted(expr2.depends, key=lambda v: v.name)
            [w: float32, x: float32, y: float32, z: float32]

        """
        return AugExpr.format(fmt, *deps, **kwdeps)

    def expr_from_lambda(self, lamb: Lambda) -> AugExpr:
        depends = set(SfgKernelParamVar(p) for p in lamb.parameters)
        code = lamb.c_code()
        return AugExpr.make(code, depends, dtype=lamb.return_type)

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

    def switch(self, switch_arg: ExprLike, autobreak: bool = True) -> SfgSwitchBuilder:
        """Use inside a function to construct a switch-case statement.

        Args:
            switch_arg: Argument to the `switch()` statement
            autobreak: Whether to automatically print a ``break;`` at the end of each case block
        """
        return SfgSwitchBuilder(switch_arg, autobreak=autobreak)

    def map_field(
        self,
        field: Field,
        index_provider: SupportsFieldExtraction,
        cast_indexing_symbols: bool = True,
    ) -> SfgDeferredFieldMapping:
        """Map a pystencils field to a field data structure, from which pointers, sizes
        and strides should be extracted.

        Args:
            field: The pystencils field to be mapped
            index_provider: An object that provides the field indexing information
            cast_indexing_symbols: Whether to always introduce explicit casts for indexing symbols
        """
        return SfgDeferredFieldMapping(
            field, index_provider, cast_indexing_symbols=cast_indexing_symbols
        )

    def set_param(self, param: VarLike | sp.Symbol, expr: ExprLike):
        """Set a kernel parameter to an expression.

        Code setting the parameter will only be generated if the parameter
        is actually alive (i.e. required by some kernel, and not yet set) at
        the point this method is called.
        """
        var: SfgVar | sp.Symbol = asvar(param) if isinstance(param, _VarLike) else param
        return SfgDeferredParamSetter(var, expr)

    def map_vector(
        self,
        lhs_components: Sequence[VarLike | sp.Symbol],
        rhs: SupportsVectorExtraction,
    ):
        """Extracts scalar numerical values from a vector data type.

        Args:
            lhs_components: Vector components as a list of symbols.
            rhs: An object providing access to vector components
        """
        components: list[SfgVar | sp.Symbol] = [
            (asvar(c) if isinstance(c, _VarLike) else c) for c in lhs_components
        ]
        return SfgDeferredVectorMapping(components, rhs)


def make_statements(arg: ExprLike) -> SfgStatements:
    return SfgStatements(str(arg), (), depends(arg), includes(arg))


def make_sequence(*args: SequencerArg) -> SfgSequence:
    """Construct a sequence of C++ code from various kinds of arguments.

    `make_sequence` is ubiquitous throughout the function building front-end;
    among others, it powers the syntax of `SfgBasicComposer.function`
    and `SfgBasicComposer.branch`.

    `make_sequence` constructs an abstract syntax tree for code within a function body, accepting various
    types of arguments which then get turned into C++ code. These are

    - Strings (`str`) are printed as-is
    - Tuples (`tuple`) signify *blocks*, i.e. C++ code regions enclosed in ``{ }``
    - Sub-ASTs and AST builders, which are often produced by the syntactic sugar and
      factory methods of `SfgComposer`.

    :Example:

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
        elif isinstance(arg, _ExprLike):
            children.append(make_statements(arg))
        elif isinstance(arg, tuple):
            #   Tuples are treated as blocks
            subseq = make_sequence(*arg)
            children.append(SfgBlock(subseq))
        else:
            raise TypeError(f"Sequence argument {i} has invalid type.")

    return SfgSequence(children)


class SfgFunctionSequencerBase:
    """Common base class for function and method sequencers.

    This builder uses call sequencing to specify the function or method's properties.

    Example:

    >>> sfg.function(
    ...         "myFunction"
    ...     ).returns(
    ...         "float32"
    ...     ).attr(
    ...         "nodiscard", "maybe_unused"
    ...     ).inline().constexpr()(
    ...         "return 31.2;"
    ...     )
    """

    def __init__(self, cursor: SfgCursor, name: str) -> None:
        self._cursor = cursor
        self._name = name
        self._return_type: PsType = void
        self._params: list[SfgVar] | None = None

        #   Qualifiers
        self._inline: bool = False
        self._constexpr: bool = False

        #   Attributes
        self._attributes: list[str] = []

    def returns(self, rtype: UserTypeSpec):
        """Set the return type of the function"""
        self._return_type = create_type(rtype)
        return self

    def params(self, *args: VarLike):
        """Specify the parameters for this function.

        Use this to manually specify the function's parameter list.

        If any free variables collected from the function body are not contained
        in the parameter list, an error will be raised.
        """
        self._params = [asvar(v) for v in args]
        return self

    def inline(self):
        """Mark this function as ``inline``."""
        self._inline = True
        return self

    def constexpr(self):
        """Mark this function as ``constexpr``."""
        self._constexpr = True
        return self

    def attr(self, *attrs: str):
        """Add attributes to this function"""
        self._attributes += attrs
        return self


class SfgFunctionSequencer(SfgFunctionSequencerBase):
    """Sequencer for constructing functions."""

    def __call__(self, *args: SequencerArg) -> None:
        """Populate the function body"""
        tree = make_sequence(*args)
        func = SfgFunction(
            self._name,
            self._cursor.current_namespace,
            tree,
            return_type=self._return_type,
            inline=self._inline,
            constexpr=self._constexpr,
            attributes=self._attributes,
            required_params=self._params,
        )
        self._cursor.add_entity(func)

        if self._inline:
            self._cursor.write_header(SfgEntityDef(func))
        else:
            self._cursor.write_header(SfgEntityDecl(func))
            self._cursor.write_impl(SfgEntityDef(func))


class SfgBranchBuilder(SfgNodeBuilder):
    """Multi-call builder for C++ ``if/else`` statements."""

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
    """Builder for C++ switches."""

    def __init__(self, switch_arg: ExprLike, autobreak: bool = True):
        self._switch_arg = switch_arg
        self._cases: dict[str, SfgSequence] = dict()
        self._default: SfgSequence | None = None
        self._autobreak = autobreak

    def case(self, label: str):
        if label in self._cases:
            raise SfgException(f"Duplicate case: {label}")

        def sequencer(*args: SequencerArg):
            if self._autobreak:
                args += ("break;",)
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
