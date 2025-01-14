from __future__ import annotations

from abc import ABC
from enum import Enum, auto
from typing import TYPE_CHECKING, Sequence, Generator, TypeVar
from dataclasses import replace
from itertools import chain

from pystencils import CreateKernelConfig, create_kernel, Field
from pystencils.codegen import Kernel, Parameter
from pystencils.types import PsType, PsCustomType

from ..lang import SfgVar, HeaderFile, void
from ..exceptions import SfgException

if TYPE_CHECKING:
    from . import SfgCallTreeNode
    from ..context import SfgContext


class SfgEmptyLines:
    def __init__(self, lines: int):
        self._lines = lines

    @property
    def lines(self) -> int:
        return self._lines


class SfgHeaderInclude:
    """Represent ``#include``-directives."""

    def __init__(
        self, header_file: HeaderFile, private: bool = False
    ):
        self._header_file = header_file
        self._private = private

    @property
    def file(self) -> str:
        return self._header_file.filepath

    @property
    def system_header(self):
        return self._header_file.system_header

    @property
    def private(self):
        return self._private

    def __hash__(self) -> int:
        return hash((self._header_file, self._private))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SfgHeaderInclude)
            and self._header_file == other._header_file
            and self._private == other._private
        )


class SfgKernelNamespace:
    """A namespace grouping together a number of kernels."""

    def __init__(self, ctx: SfgContext, name: str):
        self._ctx = ctx
        self._name = name
        self._kernel_functions: dict[str, Kernel] = dict()

    @property
    def name(self):
        return self._name

    @property
    def kernel_functions(self):
        yield from self._kernel_functions.values()

    def get_kernel_function(self, khandle: SfgKernelHandle) -> Kernel:
        if khandle.kernel_namespace is not self:
            raise ValueError(
                f"Kernel handle does not belong to this namespace: {khandle}"
            )

        return self._kernel_functions[khandle.kernel_name]

    def add(self, kernel: Kernel, name: str | None = None):
        """Adds an existing pystencils AST to this namespace.
        If a name is specified, the AST's function name is changed."""
        if name is not None:
            astname = name
        else:
            astname = kernel.name

        if astname in self._kernel_functions:
            raise ValueError(
                f"Duplicate ASTs: An AST with name {astname} already exists in namespace {self._name}"
            )

        if name is not None:
            kernel.name = name

        self._kernel_functions[astname] = kernel

        for header in kernel.required_headers:
            self._ctx.add_include(SfgHeaderInclude(HeaderFile.parse(header), private=True))

        return SfgKernelHandle(self._ctx, astname, self, kernel.parameters)

    def create(
        self,
        assignments,
        name: str | None = None,
        config: CreateKernelConfig | None = None,
    ):
        """Creates a new pystencils kernel from a list of assignments and a configuration.
        This is a wrapper around `pystencils.create_kernel`
        with a subsequent call to `add`.
        """
        if config is None:
            config = CreateKernelConfig()

        if name is not None:
            if name in self._kernel_functions:
                raise ValueError(
                    f"Duplicate ASTs: An AST with name {name} already exists in namespace {self._name}"
                )
            config = replace(config, function_name=name)

        # type: ignore
        ast = create_kernel(assignments, config=config)
        return self.add(ast)


class SfgKernelHandle:
    """A handle that represents a pystencils kernel within a kernel namespace."""

    def __init__(
        self,
        ctx: SfgContext,
        name: str,
        namespace: SfgKernelNamespace,
        parameters: Sequence[Parameter],
    ):
        self._ctx = ctx
        self._name = name
        self._namespace = namespace
        self._parameters = [SfgKernelParamVar(p) for p in parameters]

        self._scalar_params: set[SfgVar] = set()
        self._fields: set[Field] = set()

        for param in self._parameters:
            if param.wrapped.is_field_parameter:
                self._fields |= set(param.wrapped.fields)
            else:
                self._scalar_params.add(param)

    @property
    def kernel_name(self):
        return self._name

    @property
    def kernel_namespace(self):
        return self._namespace

    @property
    def fully_qualified_name(self):
        match self._ctx.fully_qualified_namespace:
            case None:
                return f"{self.kernel_namespace.name}::{self.kernel_name}"
            case fqn:
                return f"{fqn}::{self.kernel_namespace.name}::{self.kernel_name}"

    @property
    def parameters(self) -> Sequence[SfgKernelParamVar]:
        return self._parameters

    @property
    def scalar_parameters(self) -> set[SfgVar]:
        return self._scalar_params

    @property
    def fields(self):
        return self._fields

    def get_kernel_function(self) -> Kernel:
        return self._namespace.get_kernel_function(self)


SymbolLike_T = TypeVar("SymbolLike_T", bound=Parameter)


class SfgKernelParamVar(SfgVar):
    __match_args__ = ("wrapped",)

    """Cast pystencils- or SymPy-native symbol-like objects as a `SfgVar`."""

    def __init__(self, param: Parameter):
        self._param = param
        super().__init__(param.name, param.dtype)

    @property
    def wrapped(self) -> Parameter:
        return self._param

    def _args(self):
        return (self._param,)


class SfgFunction:
    __match_args__ = ("name", "tree", "parameters")

    def __init__(
        self,
        name: str,
        tree: SfgCallTreeNode,
        return_type: PsType = void,
        _is_method: bool = False,
    ):
        self._name = name
        self._tree = tree
        self._return_type = return_type

        self._parameters: set[SfgVar]
        if not _is_method:
            from .postprocessing import CallTreePostProcessing

            param_collector = CallTreePostProcessing()
            self._parameters = param_collector(self._tree).function_params

    @property
    def name(self) -> str:
        return self._name

    @property
    def parameters(self) -> set[SfgVar]:
        return self._parameters

    @property
    def tree(self) -> SfgCallTreeNode:
        return self._tree

    @property
    def return_type(self) -> PsType:
        return self._return_type


class SfgVisibility(Enum):
    DEFAULT = auto()
    PRIVATE = auto()
    PROTECTED = auto()
    PUBLIC = auto()

    def __str__(self) -> str:
        match self:
            case SfgVisibility.DEFAULT:
                return ""
            case SfgVisibility.PRIVATE:
                return "private"
            case SfgVisibility.PROTECTED:
                return "protected"
            case SfgVisibility.PUBLIC:
                return "public"


class SfgClassKeyword(Enum):
    STRUCT = auto()
    CLASS = auto()

    def __str__(self) -> str:
        match self:
            case SfgClassKeyword.STRUCT:
                return "struct"
            case SfgClassKeyword.CLASS:
                return "class"


class SfgClassMember(ABC):
    def __init__(self) -> None:
        self._cls: SfgClass | None = None
        self._visibility: SfgVisibility | None = None

    @property
    def owning_class(self) -> SfgClass:
        if self._cls is None:
            raise SfgException(f"{self} is not bound to a class.")
        return self._cls

    @property
    def visibility(self) -> SfgVisibility:
        if self._visibility is None:
            raise SfgException(
                f"{self} is not bound to a class and therefore has no visibility."
            )
        return self._visibility

    @property
    def is_bound(self) -> bool:
        return self._cls is not None

    def _bind(self, cls: SfgClass, vis: SfgVisibility):
        if self.is_bound:
            raise SfgException(
                f"Binding {self} to class {cls.class_name} failed: "
                f"{self} was already bound to {self.owning_class.class_name}"
            )
        self._cls = cls
        self._vis = vis


class SfgVisibilityBlock:
    def __init__(self, visibility: SfgVisibility) -> None:
        self._vis = visibility
        self._members: list[SfgClassMember] = []
        self._cls: SfgClass | None = None

    @property
    def visibility(self) -> SfgVisibility:
        return self._vis

    def append_member(self, member: SfgClassMember):
        if self._cls is not None:
            self._cls._add_member(member, self._vis)
        self._members.append(member)

    def members(self) -> Generator[SfgClassMember, None, None]:
        yield from self._members

    @property
    def is_bound(self) -> bool:
        return self._cls is not None

    def _bind(self, cls: SfgClass):
        if self._cls is not None:
            raise SfgException(
                f"Binding visibility block to class {cls.class_name} failed: "
                f"was already bound to {self._cls.class_name}"
            )
        self._cls = cls


class SfgInClassDefinition(SfgClassMember):
    def __init__(self, text: str):
        SfgClassMember.__init__(self)
        self._text = text

    @property
    def text(self) -> str:
        return self._text

    def __str__(self) -> str:
        return self._text


class SfgMemberVariable(SfgVar, SfgClassMember):
    def __init__(self, name: str, dtype: PsType):
        SfgVar.__init__(self, name, dtype)
        SfgClassMember.__init__(self)


class SfgMethod(SfgFunction, SfgClassMember):
    def __init__(
        self,
        name: str,
        tree: SfgCallTreeNode,
        return_type: PsType = PsCustomType("void"),
        inline: bool = False,
        const: bool = False,
    ):
        SfgFunction.__init__(self, name, tree, return_type=return_type, _is_method=True)
        SfgClassMember.__init__(self)

        self._inline = inline
        self._const = const
        self._parameters: set[SfgVar] = set()

    @property
    def inline(self) -> bool:
        return self._inline

    @property
    def const(self) -> bool:
        return self._const

    def _bind(self, cls: SfgClass, vis: SfgVisibility):
        super()._bind(cls, vis)

        from .postprocessing import CallTreePostProcessing

        param_collector = CallTreePostProcessing(enclosing_class=cls)
        self._parameters = param_collector(self._tree).function_params


class SfgConstructor(SfgClassMember):
    __match_args__ = ("parameters", "initializers", "body")

    def __init__(
        self,
        parameters: Sequence[SfgVar] = (),
        initializers: Sequence[str] = (),
        body: str = "",
    ):
        SfgClassMember.__init__(self)
        self._parameters = tuple(parameters)
        self._initializers = tuple(initializers)
        self._body = body

    @property
    def parameters(self) -> tuple[SfgVar, ...]:
        return self._parameters

    @property
    def initializers(self) -> tuple[str, ...]:
        return self._initializers

    @property
    def body(self) -> str:
        return self._body


class SfgClass:
    """Models a C++ class.

    ### Adding members to classes

    Members are never added directly to a class. Instead, they are added to
    an [SfgVisibilityBlock][pystencilssfg.source_components.SfgVisibilityBlock]
    which defines their syntactic position and visibility modifier in the code.
    At the top of every class, there is a default visibility block
    accessible through the `default` property.
    To add members with custom visibility, create a new SfgVisibilityBlock,
    add members to the block, and add the block using `append_visibility_block`.

    A more succinct interface for constructing classes is available through the
    [SfgClassComposer][pystencilssfg.composer.SfgClassComposer].
    """

    __match_args__ = ("class_name",)

    def __init__(
        self,
        class_name: str,
        class_keyword: SfgClassKeyword = SfgClassKeyword.CLASS,
        bases: Sequence[str] = (),
    ):
        if isinstance(bases, str):
            raise ValueError("Base classes must be given as a sequence.")

        self._class_name = class_name
        self._class_keyword = class_keyword
        self._bases_classes = tuple(bases)

        self._default_block = SfgVisibilityBlock(SfgVisibility.DEFAULT)
        self._default_block._bind(self)
        self._blocks = [self._default_block]

        self._definitions: list[SfgInClassDefinition] = []
        self._constructors: list[SfgConstructor] = []
        self._methods: list[SfgMethod] = []
        self._member_vars: dict[str, SfgMemberVariable] = dict()

    @property
    def class_name(self) -> str:
        return self._class_name

    @property
    def src_type(self) -> PsType:
        return PsCustomType(self._class_name)

    @property
    def base_classes(self) -> tuple[str, ...]:
        return self._bases_classes

    @property
    def class_keyword(self) -> SfgClassKeyword:
        return self._class_keyword

    @property
    def default(self) -> SfgVisibilityBlock:
        return self._default_block

    def append_visibility_block(self, block: SfgVisibilityBlock):
        if block.visibility == SfgVisibility.DEFAULT:
            raise SfgException(
                "Can't add another block with DEFAULT visibility to a class. Use `.default` instead."
            )

        block._bind(self)
        for m in block.members():
            self._add_member(m, block.visibility)
        self._blocks.append(block)

    def visibility_blocks(self) -> Generator[SfgVisibilityBlock, None, None]:
        yield from self._blocks

    def members(
        self, visibility: SfgVisibility | None = None
    ) -> Generator[SfgClassMember, None, None]:
        if visibility is None:
            yield from chain.from_iterable(b.members() for b in self._blocks)
        else:
            yield from chain.from_iterable(
                b.members()
                for b in filter(lambda b: b.visibility == visibility, self._blocks)
            )

    def definitions(
        self, visibility: SfgVisibility | None = None
    ) -> Generator[SfgInClassDefinition, None, None]:
        if visibility is not None:
            yield from filter(lambda m: m.visibility == visibility, self._definitions)
        else:
            yield from self._definitions

    def member_variables(
        self, visibility: SfgVisibility | None = None
    ) -> Generator[SfgMemberVariable, None, None]:
        if visibility is not None:
            yield from filter(
                lambda m: m.visibility == visibility, self._member_vars.values()
            )
        else:
            yield from self._member_vars.values()

    def constructors(
        self, visibility: SfgVisibility | None = None
    ) -> Generator[SfgConstructor, None, None]:
        if visibility is not None:
            yield from filter(lambda m: m.visibility == visibility, self._constructors)
        else:
            yield from self._constructors

    def methods(
        self, visibility: SfgVisibility | None = None
    ) -> Generator[SfgMethod, None, None]:
        if visibility is not None:
            yield from filter(lambda m: m.visibility == visibility, self._methods)
        else:
            yield from self._methods

    # PRIVATE

    def _add_member(self, member: SfgClassMember, vis: SfgVisibility):
        if isinstance(member, SfgConstructor):
            self._add_constructor(member)
        elif isinstance(member, SfgMemberVariable):
            self._add_member_variable(member)
        elif isinstance(member, SfgMethod):
            self._add_method(member)
        elif isinstance(member, SfgInClassDefinition):
            self._add_definition(member)
        else:
            raise SfgException(f"{member} is not a valid class member.")

        member._bind(self, vis)

    def _add_definition(self, definition: SfgInClassDefinition):
        self._definitions.append(definition)

    def _add_constructor(self, constr: SfgConstructor):
        self._constructors.append(constr)

    def _add_method(self, method: SfgMethod):
        self._methods.append(method)

    def _add_member_variable(self, variable: SfgMemberVariable):
        if variable.name in self._member_vars:
            raise SfgException(
                f"Duplicate field name {variable.name} in class {self._class_name}"
            )

        self._member_vars[variable.name] = variable
