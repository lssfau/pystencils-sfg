from __future__ import annotations

from dataclasses import dataclass
from abc import ABC
from enum import Enum, auto
from typing import (
    TYPE_CHECKING,
    Sequence,
    Generator,
)
from itertools import chain

from pystencils import Field
from pystencils.codegen import Kernel
from pystencils.types import PsType, PsCustomType

from ..lang import SfgVar, SfgKernelParamVar, void, ExprLike
from ..exceptions import SfgException

if TYPE_CHECKING:
    from . import SfgCallTreeNode


#   =========================================================================================================
#
#   SEMANTICAL ENTITIES
#
#   These classes model *code entities*, which represent *semantic components* of the generated files.
#
#   =========================================================================================================


class SfgCodeEntity:
    """Base class for code entities.

    Each code entity has a name and an optional enclosing namespace.
    """

    def __init__(self, name: str, parent_namespace: SfgNamespace) -> None:
        self._name = name
        self._namespace: SfgNamespace = parent_namespace

    @property
    def name(self) -> str:
        """Name of this entity"""
        return self._name

    @property
    def fqname(self) -> str:
        """Fully qualified name of this entity"""
        if not isinstance(self._namespace, SfgGlobalNamespace):
            return self._namespace.fqname + "::" + self._name
        else:
            return self._name

    @property
    def parent_namespace(self) -> SfgNamespace | None:
        """Parent namespace of this entity"""
        return self._namespace


class SfgNamespace(SfgCodeEntity):
    """A C++ namespace.

    Each namespace has a name and a parent; its fully qualified name is given as
    ``<parent.name>::<name>``.

    Args:
        name: Local name of this namespace
        parent: Parent namespace enclosing this namespace
    """

    def __init__(self, name: str, parent_namespace: SfgNamespace) -> None:
        super().__init__(name, parent_namespace)

        self._entities: dict[str, SfgCodeEntity] = dict()

    def get_entity(self, qual_name: str) -> SfgCodeEntity | None:
        """Find an entity with the given qualified name within this namespace.

        If ``qual_name`` contains any qualifying delimiters ``::``,
        each component but the last is interpreted as a namespace.
        """
        tokens = qual_name.split("::", 1)
        match tokens:
            case [entity_name]:
                return self._entities.get(entity_name, None)
            case [nspace, remaining_qualname]:
                sub_nspace = self._entities.get(nspace, None)
                if sub_nspace is not None:
                    if not isinstance(sub_nspace, SfgNamespace):
                        raise KeyError(
                            f"Unable to find entity {qual_name} in namespace {self._name}: "
                            f"Entity {nspace} is not a namespace."
                        )
                    return sub_nspace.get_entity(remaining_qualname)
                else:
                    return None
            case _:
                assert False, "unreachable code"

    def add_entity(self, entity: SfgCodeEntity):
        if entity.name in self._entities:
            raise ValueError(
                f"Another entity with the name {entity.fqname} already exists"
            )
        self._entities[entity.name] = entity

    def get_child_namespace(self, qual_name: str):
        if not qual_name:
            raise ValueError("Anonymous namespaces are not supported")

        #   Find the namespace by qualified lookup ...
        namespace = self.get_entity(qual_name)
        if namespace is not None:
            if not type(namespace) is SfgNamespace:
                raise ValueError(f"Entity {qual_name} exists, but is not a namespace")
        else:
            #   ... or create it
            tokens = qual_name.split("::")
            namespace = self
            for tok in tokens:
                namespace = SfgNamespace(tok, namespace)

        return namespace


class SfgGlobalNamespace(SfgNamespace):
    """The C++ global namespace."""

    def __init__(self) -> None:
        super().__init__("", self)

    @property
    def fqname(self) -> str:
        return ""


class SfgKernelHandle(SfgCodeEntity):
    """Handle to a pystencils kernel."""

    __match_args__ = ("kernel", "parameters")

    def __init__(
        self,
        name: str,
        namespace: SfgKernelNamespace,
        kernel: Kernel,
        inline: bool = False,
    ):
        super().__init__(name, namespace)

        self._kernel = kernel
        self._parameters = [SfgKernelParamVar(p) for p in kernel.parameters]

        self._inline: bool = inline

        self._scalar_params: set[SfgVar] = set()
        self._fields: set[Field] = set()

        for param in self._parameters:
            if param.wrapped.is_field_parameter:
                self._fields |= set(param.wrapped.fields)
            else:
                self._scalar_params.add(param)

    @property
    def parameters(self) -> Sequence[SfgKernelParamVar]:
        """Parameters to this kernel"""
        return self._parameters

    @property
    def scalar_parameters(self) -> set[SfgVar]:
        """Scalar parameters to this kernel"""
        return self._scalar_params

    @property
    def fields(self):
        """Fields accessed by this kernel"""
        return self._fields

    @property
    def kernel(self) -> Kernel:
        """Underlying pystencils kernel object"""
        return self._kernel

    @property
    def inline(self) -> bool:
        return self._inline


class SfgKernelNamespace(SfgNamespace):
    """A namespace grouping together a number of kernels."""

    def __init__(self, name: str, parent: SfgNamespace):
        super().__init__(name, parent)
        self._kernels: dict[str, SfgKernelHandle] = dict()

    @property
    def name(self):
        return self._name

    @property
    def kernels(self) -> tuple[SfgKernelHandle, ...]:
        return tuple(self._kernels.values())

    def find_kernel(self, name: str) -> SfgKernelHandle | None:
        return self._kernels.get(name, None)

    def add_kernel(self, kernel: SfgKernelHandle):
        if kernel.name in self._kernels:
            raise ValueError(
                f"Duplicate kernels: A kernel called {kernel.name} already exists "
                f"in namespace {self.fqname}"
            )
        self._kernels[kernel.name] = kernel


@dataclass(frozen=True, match_args=False)
class CommonFunctionProperties:
    tree: SfgCallTreeNode
    parameters: tuple[SfgVar, ...]
    return_type: PsType
    inline: bool
    constexpr: bool
    attributes: Sequence[str]

    @staticmethod
    def collect_params(tree: SfgCallTreeNode, required_params: Sequence[SfgVar] | None):
        from .postprocessing import CallTreePostProcessing

        param_collector = CallTreePostProcessing()
        params_set = param_collector(tree).function_params

        if required_params is not None:
            if not (params_set <= set(required_params)):
                extras = params_set - set(required_params)
                raise SfgException(
                    "Extraenous function parameters: "
                    f"Found free variables {extras} that were not listed in manually specified function parameters."
                )
            parameters = tuple(required_params)
        else:
            parameters = tuple(sorted(params_set, key=lambda p: p.name))

        return parameters


class SfgFunction(SfgCodeEntity, CommonFunctionProperties):
    """A free function."""

    __match_args__ = ("name", "tree", "parameters", "return_type")  # type: ignore

    def __init__(
        self,
        name: str,
        namespace: SfgNamespace,
        tree: SfgCallTreeNode,
        return_type: PsType = void,
        inline: bool = False,
        constexpr: bool = False,
        attributes: Sequence[str] = (),
        required_params: Sequence[SfgVar] | None = None,
    ):
        super().__init__(name, namespace)

        parameters = self.collect_params(tree, required_params)

        CommonFunctionProperties.__init__(
            self,
            tree,
            parameters,
            return_type,
            inline,
            constexpr,
            attributes,
        )


class SfgVisibility(Enum):
    """Visibility qualifiers of C++"""

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
    """Class keywords of C++"""

    STRUCT = auto()
    CLASS = auto()

    def __str__(self) -> str:
        match self:
            case SfgClassKeyword.STRUCT:
                return "struct"
            case SfgClassKeyword.CLASS:
                return "class"


class SfgClassMember(ABC):
    """Base class for class member entities"""

    def __init__(self, cls: SfgClass) -> None:
        self._cls: SfgClass = cls
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


class SfgMemberVariable(SfgVar, SfgClassMember):
    """Variable that is a field of a class"""

    def __init__(
        self,
        name: str,
        dtype: PsType,
        cls: SfgClass,
        default_init: tuple[ExprLike, ...] | None = None,
    ):
        SfgVar.__init__(self, name, dtype)
        SfgClassMember.__init__(self, cls)
        self._default_init = default_init

    @property
    def default_init(self) -> tuple[ExprLike, ...] | None:
        return self._default_init


class SfgMethod(SfgClassMember, CommonFunctionProperties):
    """Instance method of a class"""

    __match_args__ = ("name", "tree", "parameters", "return_type")  # type: ignore

    def __init__(
        self,
        name: str,
        cls: SfgClass,
        tree: SfgCallTreeNode,
        return_type: PsType = void,
        inline: bool = False,
        const: bool = False,
        static: bool = False,
        constexpr: bool = False,
        virtual: bool = False,
        override: bool = False,
        attributes: Sequence[str] = (),
        required_params: Sequence[SfgVar] | None = None,
    ):
        super().__init__(cls)

        self._name = name
        self._static = static
        self._const = const
        self._virtual = virtual
        self._override = override

        parameters = self.collect_params(tree, required_params)

        CommonFunctionProperties.__init__(
            self,
            tree,
            parameters,
            return_type,
            inline,
            constexpr,
            attributes,
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def static(self) -> bool:
        return self._static

    @property
    def const(self) -> bool:
        return self._const

    @property
    def virtual(self) -> bool:
        return self._virtual

    @property
    def override(self) -> bool:
        return self._override


class SfgConstructor(SfgClassMember):
    """Constructor of a class"""

    __match_args__ = ("owning_class", "parameters", "initializers", "body")

    def __init__(
        self,
        cls: SfgClass,
        parameters: Sequence[SfgVar] = (),
        initializers: Sequence[tuple[SfgVar | str, tuple[ExprLike, ...]]] = (),
        body: str = "",
    ):
        super().__init__(cls)
        self._parameters = tuple(parameters)
        self._initializers = tuple(initializers)
        self._body = body

    @property
    def parameters(self) -> tuple[SfgVar, ...]:
        return self._parameters

    @property
    def initializers(self) -> tuple[tuple[SfgVar | str, tuple[ExprLike, ...]], ...]:
        return self._initializers

    @property
    def body(self) -> str:
        return self._body


class SfgClass(SfgCodeEntity):
    """A C++ class."""

    __match_args__ = ("class_keyword", "name")

    def __init__(
        self,
        name: str,
        namespace: SfgNamespace,
        class_keyword: SfgClassKeyword = SfgClassKeyword.CLASS,
        bases: Sequence[str] = (),
    ):
        if isinstance(bases, str):
            raise ValueError("Base classes must be given as a sequence.")

        super().__init__(name, namespace)

        self._class_keyword = class_keyword
        self._bases_classes = tuple(bases)

        self._constructors: list[SfgConstructor] = []
        self._methods: list[SfgMethod] = []
        self._member_vars: dict[str, SfgMemberVariable] = dict()

    @property
    def src_type(self) -> PsType:
        #   TODO: Use CppTypeFactory instead
        return PsCustomType(self._name)

    @property
    def base_classes(self) -> tuple[str, ...]:
        return self._bases_classes

    @property
    def class_keyword(self) -> SfgClassKeyword:
        return self._class_keyword

    def members(
        self, visibility: SfgVisibility | None = None
    ) -> Generator[SfgClassMember, None, None]:
        if visibility is None:
            yield from chain(
                self._constructors, self._methods, self._member_vars.values()
            )
        else:
            yield from filter(lambda m: m.visibility == visibility, self.members())

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

    def add_member(self, member: SfgClassMember, vis: SfgVisibility):
        if isinstance(member, SfgConstructor):
            self._constructors.append(member)
        elif isinstance(member, SfgMemberVariable):
            self._add_member_variable(member)
        elif isinstance(member, SfgMethod):
            self._methods.append(member)
        else:
            raise SfgException(f"{member} is not a valid class member.")

    def _add_member_variable(self, variable: SfgMemberVariable):
        if variable.name in self._member_vars:
            raise SfgException(
                f"Duplicate field name {variable.name} in class {self._name}"
            )

        self._member_vars[variable.name] = variable
