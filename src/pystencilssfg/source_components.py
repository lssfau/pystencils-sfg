from __future__ import annotations

from abc import ABC
from enum import Enum, auto
from typing import TYPE_CHECKING, Sequence, Generator
from dataclasses import replace

from pystencils import CreateKernelConfig, create_kernel
from pystencils.astnodes import KernelFunction

from .types import SrcType
from .source_concepts import SrcObject
from .exceptions import SfgException

if TYPE_CHECKING:
    from .tree import SfgCallTreeNode


class SfgEmptyLines:
    def __init__(self, lines: int):
        self._lines = lines

    @property
    def lines(self) -> int:
        return self._lines


class SfgHeaderInclude:
    def __init__(
        self, header_file: str, system_header: bool = False, private: bool = False
    ):
        self._header_file = header_file
        self._system_header = system_header
        self._private = private

    @property
    def file(self) -> str:
        return self._header_file

    @property
    def system_header(self):
        return self._system_header

    @property
    def private(self):
        return self._private

    def __hash__(self) -> int:
        return hash((self._header_file, self._system_header, self._private))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SfgHeaderInclude)
            and self._header_file == other._header_file
            and self._system_header == other._system_header
            and self._private == other._private
        )


class SfgKernelNamespace:
    def __init__(self, ctx, name: str):
        self._ctx = ctx
        self._name = name
        self._asts: dict[str, KernelFunction] = dict()

    @property
    def name(self):
        return self._name

    @property
    def asts(self):
        yield from self._asts.values()

    def add(self, ast: KernelFunction, name: str | None = None):
        """Adds an existing pystencils AST to this namespace.
        If a name is specified, the AST's function name is changed."""
        if name is not None:
            astname = name
        else:
            astname = ast.function_name

        if astname in self._asts:
            raise ValueError(
                f"Duplicate ASTs: An AST with name {astname} already exists in namespace {self._name}"
            )

        if name is not None:
            ast.function_name = name

        self._asts[astname] = ast

        return SfgKernelHandle(self._ctx, astname, self, ast.get_parameters())

    def create(
        self,
        assignments,
        name: str | None = None,
        config: CreateKernelConfig | None = None,
    ):
        """Creates a new pystencils kernel from a list of assignments and a configuration.
        This is a wrapper around
        [`pystencils.create_kernel`](
            https://pycodegen.pages.i10git.cs.fau.de/pystencils/
            sphinx/kernel_compile_and_call.html#pystencils.create_kernel
        )
        with a subsequent call to [`add`][pystencilssfg.source_components.SfgKernelNamespace.add].
        """
        if config is None:
            config = CreateKernelConfig()

        if name is not None:
            if name in self._asts:
                raise ValueError(
                    f"Duplicate ASTs: An AST with name {name} already exists in namespace {self._name}"
                )
            config = replace(config, function_name=name)

        # type: ignore
        ast = create_kernel(assignments, config=config)
        return self.add(ast)


class SfgKernelHandle:
    def __init__(
        self,
        ctx,
        name: str,
        namespace: SfgKernelNamespace,
        parameters: Sequence[KernelFunction.Parameter],
    ):
        self._ctx = ctx
        self._name = name
        self._namespace = namespace
        self._parameters = parameters

        self._scalar_params = set()
        self._fields = set()

        for param in self._parameters:
            if param.is_field_parameter:
                self._fields |= set(param.fields)
            else:
                self._scalar_params.add(param.symbol)

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
    def parameters(self):
        return self._parameters

    @property
    def scalar_parameters(self):
        return self._scalar_params

    @property
    def fields(self):
        return self.fields


class SfgFunction:
    def __init__(
        self, name: str, tree: SfgCallTreeNode, return_type: SrcType = SrcType("void")
    ):
        self._name = name
        self._tree = tree
        self._return_type = return_type

        from .visitors.tree_visitors import ExpandingParameterCollector

        param_collector = ExpandingParameterCollector()
        self._parameters = param_collector.visit(self._tree)

    @property
    def name(self):
        return self._name

    @property
    def parameters(self):
        return self._parameters

    @property
    def tree(self):
        return self._tree

    @property
    def return_type(self) -> SrcType:
        return self._return_type


class SfgVisibility(Enum):
    DEFAULT = auto()
    PRIVATE = auto()
    PUBLIC = auto()

    def __str__(self) -> str:
        match self:
            case SfgVisibility.DEFAULT:
                return ""
            case SfgVisibility.PRIVATE:
                return "private"
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
    def __init__(self, cls: SfgClass, visibility: SfgVisibility):
        self._cls = cls
        self._visibility = visibility

    @property
    def owning_class(self) -> SfgClass:
        return self._cls

    @property
    def visibility(self) -> SfgVisibility:
        return self._visibility


class SfgMemberVariable(SrcObject, SfgClassMember):
    def __init__(
        self,
        name: str,
        type: SrcType,
        cls: SfgClass,
        visibility: SfgVisibility = SfgVisibility.PRIVATE,
    ):
        SrcObject.__init__(self, name, type)
        SfgClassMember.__init__(self, cls, visibility)


class SfgMethod(SfgFunction, SfgClassMember):
    def __init__(
        self,
        name: str,
        tree: SfgCallTreeNode,
        cls: SfgClass,
        visibility: SfgVisibility = SfgVisibility.PUBLIC,
        return_type: SrcType = SrcType("void"),
        inline: bool = False,
        const: bool = False,
    ):
        SfgFunction.__init__(self, name, tree, return_type=return_type)
        SfgClassMember.__init__(self, cls, visibility)

        self._inline = inline
        self._const = const

    @property
    def inline(self) -> bool:
        return self._inline

    @property
    def const(self) -> bool:
        return self._const


class SfgConstructor(SfgClassMember):
    def __init__(
        self,
        cls: SfgClass,
        parameters: Sequence[SrcObject] = (),
        initializers: Sequence[str] = (),
        body: str = "",
        visibility: SfgVisibility = SfgVisibility.PUBLIC,
    ):
        SfgClassMember.__init__(self, cls, visibility)
        self._parameters = tuple(parameters)
        self._initializers = tuple(initializers)
        self._body = body

    @property
    def parameters(self) -> tuple[SrcObject, ...]:
        return self._parameters

    @property
    def initializers(self) -> tuple[str, ...]:
        return self._initializers

    @property
    def body(self) -> str:
        return self._body


class SfgClass:
    def __init__(
        self,
        class_name: str,
        class_keyword: SfgClassKeyword = SfgClassKeyword.CLASS,
        bases: Sequence[str] = (),
    ):
        self._class_name = class_name
        self._class_keyword = class_keyword
        self._bases_classes = tuple(bases)

        self._constructors: list[SfgConstructor] = []
        self._methods: dict[str, SfgMethod] = dict()
        self._member_vars: dict[str, SfgMemberVariable] = dict()

    @property
    def class_name(self) -> str:
        return self._class_name

    @property
    def src_type(self) -> SrcType:
        return SrcType(self._class_name)

    @property
    def base_classes(self) -> tuple[str, ...]:
        return self._bases_classes

    @property
    def class_keyword(self) -> SfgClassKeyword:
        return self._class_keyword

    def members(
        self, visibility: SfgVisibility | None = None
    ) -> Generator[SfgClassMember, None, None]:
        yield from self.member_variables(visibility)
        yield from self.constructors(visibility)
        yield from self.methods(visibility)

    def constructors(
        self, visibility: SfgVisibility | None = None
    ) -> Generator[SfgConstructor, None, None]:
        if visibility is not None:
            yield from filter(lambda m: m.visibility == visibility, self._constructors)
        else:
            yield from self._constructors

    def add_constructor(self, constr: SfgConstructor):
        #   TODO: Check for signature conflicts?
        self._constructors.append(constr)

    def methods(
        self, visibility: SfgVisibility | None = None
    ) -> Generator[SfgMethod, None, None]:
        if visibility is not None:
            yield from filter(
                lambda m: m.visibility == visibility, self._methods.values()
            )
        else:
            yield from self._methods.values()

    def add_method(self, method: SfgMethod):
        if method.name in self._methods:
            raise SfgException(
                f"Duplicate method name {method.name} in class {self._class_name}"
            )

        self._methods[method.name] = method

    def member_variables(
        self, visibility: SfgVisibility | None = None
    ) -> Generator[SfgMemberVariable, None, None]:
        if visibility is not None:
            yield from filter(
                lambda m: m.visibility == visibility, self._member_vars.values()
            )
        else:
            yield from self._member_vars.values()

    def add_member_variable(self, variable: SfgMemberVariable):
        if variable.name in self._member_vars:
            raise SfgException(
                f"Duplicate field name {variable.name} in class {self._class_name}"
            )

        self._member_vars[variable.name] = variable
